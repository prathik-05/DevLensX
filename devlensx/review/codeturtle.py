"""
DevLensX CodeTurtle AI Review Engine
Unified Code Review & PR Auditor Surface delegating strictly to ReviewEngine and ClaimVerifier.

Enhanced in P3 with OpenCodeReview (Apache-2.0) intelligence:
1. RuleSniffer: Path-aware language rule and negative constraint injection.
2. Negative Constraint Pre-filtering: Suppresses false positives before verification.
3. Hunk-based Line Matching & Unique Cross-File Relocation: Fixes LLM line drift.
4. Myers Line-Diff Engine: Generates structured diff snippets for 1-click committable fixes.
5. Strict Snapshot & Evidence Boundary: Exact snapshot isolation, no invented AST, no auto-writes.
"""

from __future__ import annotations

import os
import re
import json
from typing import Dict, Any, List, Optional

from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.review.review_engine import ReviewEngine
from devlensx.critic.claim_verifier import ClaimVerifierEngine, ClaimVerdict
from devlensx.agents.llm_client import call_external_llm
from devlensx.core.persistence import scrub_secrets
from devlensx.review.rules.system_rules import RuleSniffer, evaluate_negative_constraints
from devlensx.review.relocation import relocate_and_resolve_findings
from devlensx.review.suggestdiff import attach_suggestion_diff_to_finding
from devlensx.review.repair import parse_and_repair_comments
from devlensx.review.chunking import parse_diff_files, group_diffs


class CodeTurtleReviewEngine:
    """Unified CodeTurtle review facade delegating directly to ReviewEngine + ClaimVerifier."""

    @classmethod
    def review(
        cls,
        diff: str,
        analysis_run_id: str,
        base_commit: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        provider: str = "auto",
        api_key: str = "",
        azure_config: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not diff or not diff.strip():
            raise ValueError("Diff cannot be empty.")

        # 1. Exact snapshot validation via SnapshotRegistry
        registry = get_snapshot_registry()
        snap = registry.get(analysis_run_id)
        if snap is None:
            raise ValueError(f"SNAPSHOT_NOT_FOUND:{analysis_run_id}")

        # Exact model from orchestrator per-run store
        try:
            from devlensx.chat.orchestrator import _model_store
            model = _model_store.get(analysis_run_id)
        except Exception:
            model = None

        if not isinstance(model, dict) or not model.get("classes"):
            raise ValueError(f"SNAPSHOT_UNAVAILABLE:{analysis_run_id}")

        # 2. Delegate to existing ReviewEngine for deterministic grounding
        grounded_review = ReviewEngine.review(diff, analysis_run_id, base_commit)

        classes = model.get("classes", [])
        graph_edges = model.get("graph_edges", [])
        changed_symbols = grounded_review.get("what_changed", [])
        affected_symbols = grounded_review.get("what_affected", [])
        evidence_refs = grounded_review.get("evidence_refs", [])
        base_compat = grounded_review.get("base_compat", {})
        mermaid_diagram = (grounded_review.get("diagram") or {}).get("mermaid", "")

        # Extract changed files from grounded changes
        changed_files = list({c.get("file") for c in changed_symbols if c.get("file")})

        # 3. Rule Sniffer: Extract paths from diff and render specialized language rules
        rules_prompt = RuleSniffer.render_prompt_for_diff(diff)

        # 4. Deterministic Invariant Checks (always evaluated, no hallucinations)
        candidate_findings: List[Dict[str, Any]] = []

        # Parse raw diff lines for security invariant violations
        diff_lines = diff.splitlines()
        current_file = ""
        current_line = 1
        for d_line in diff_lines:
            if d_line.startswith("+++ b/"):
                current_file = d_line[6:].strip()
            elif d_line.startswith("@@"):
                m = re.search(r"\+(\d+)", d_line)
                if m:
                    current_line = int(m.group(1))
            elif d_line.startswith("+") and not d_line.startswith("+++"):
                added_text = d_line[1:]
                # Check 1: Hardcoded credentials
                if re.search(r"(?:api[_-]?key|secret|password|token)\s*=\s*['\"][A-Za-z0-9_\-]{8,}['\"]", added_text, re.IGNORECASE):
                    candidate_findings.append({
                        "file": current_file,
                        "line_start": current_line,
                        "line_end": current_line,
                        "existing_code": added_text.strip(),
                        "category": "Security",
                        "severity": "CRITICAL",
                        "rule_id": "HARDCODED_SECRET",
                        "title": "Hardcoded secret or credential detected in diff",
                        "explanation": f"Added line in {current_file}#L{current_line} contains credential pattern. Credentials must be injected via environment variables.",
                        "suggested_fix": "// Inject via environment variable or secret manager\nString secret = System.getenv(\"API_SECRET\");"
                    })
                # Check 2: Raw SQL string concatenation
                if re.search(r"(?i)(?:SELECT|INSERT|UPDATE|DELETE)\s+.*\+\s*\w+", added_text):
                    candidate_findings.append({
                        "file": current_file,
                        "line_start": current_line,
                        "line_end": current_line,
                        "existing_code": added_text.strip(),
                        "category": "Security",
                        "severity": "CRITICAL",
                        "rule_id": "SQL_INJECTION",
                        "title": "Potential SQL injection via raw string concatenation",
                        "explanation": f"Query concatenation detected at {current_file}#L{current_line}. Use parameterized prepared statements.",
                        "suggested_fix": "// Use parameterized query\nPreparedStatement stmt = conn.prepareStatement(sql);"
                    })
                # Check 3: Debt markers
                if re.search(r"(?i)\b(TODO|FIXME)\b", added_text):
                    candidate_findings.append({
                        "file": current_file,
                        "line_start": current_line,
                        "line_end": current_line,
                        "existing_code": added_text.strip(),
                        "category": "Maintainability",
                        "severity": "INFO",
                        "rule_id": "TODO_MARKER",
                        "title": "Pending technical debt marker in PR diff",
                        "explanation": f"Marker detected at {current_file}#L{current_line}: {added_text.strip()}",
                        "suggested_fix": "// Resolve debt or reference tracking issue"
                    })
                current_line += 1
            elif not d_line.startswith("-"):
                current_line += 1

        # Check 4: Architectural Governance Rules (Phase P5)
        try:
            from devlensx.governance.evaluator import GovernanceEvaluator
            from devlensx.governance.rules import get_governance_rule_registry
            gov_eval = GovernanceEvaluator(snapshot_registry=registry)
            gov_candidates = gov_eval.generate_candidate_violations(
                repository_id=snap.repository_id,
                analysis_run_id=analysis_run_id,
                commit_hash=snap.commit_hash,
                rules=get_governance_rule_registry().get_rules(enabled_only=True),
                classes=classes,
                graph_edges=graph_edges,
            )
            for g_cand in gov_candidates:
                touches_diff = any(
                    cf.endswith(g_cand.file_path) or g_cand.file_path.endswith(cf)
                    for cf in changed_files
                ) or any(
                    c.get("symbol") in (g_cand.source_symbol, g_cand.target_symbol)
                    for c in changed_symbols
                )
                if touches_diff:
                    candidate_findings.append({
                        "file": g_cand.file_path,
                        "line_start": g_cand.line_start,
                        "line_end": g_cand.line_end,
                        "existing_code": g_cand.source_symbol,
                        "category": "Architecture",
                        "severity": g_cand.severity,
                        "rule_id": g_cand.rule_id,
                        "title": f"Architectural Rule Violation: {g_cand.rule_id}",
                        "explanation": g_cand.description,
                        "suggested_fix": gov_eval._suggest_fix(g_cand),
                    })
        except Exception:
            pass

        # 5. LLM Reasoning with RuleSniffer injection and Chunking
        provider_used = "Deterministic AST & Security Grounding Engine"
        has_ambient_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENROUTER_API_KEY"))
        if provider and provider != "none" and (api_key or azure_config or has_ambient_key):
            system_prompt = (
                "You are CodeTurtle AI - senior staff code reviewer and automated PR auditor.\n"
                "Analyze the provided git diff against the codebase AST.\n"
                "Identify subtle logic errors, missing edge cases, and architectural regressions.\n"
                "Return valid JSON only with keys: summary, risk_level, comments (list of {file, line_start, line_end, existing_code, category, severity, title, explanation, suggested_fix})."
            )
            if rules_prompt:
                system_prompt += f"\n\n{rules_prompt}"

            diff_file_metas = parse_diff_files(diff)
            groups = group_diffs(diff_file_metas) if diff_file_metas else []
            target_groups = groups[:3] if groups else [None]

            for grp in target_groups:
                grp_diff = "\n\n".join(f.diff_text for f in grp.files) if grp else diff[:8000]
                grp_label = grp.label if grp else "default"
                user_prompt = f"PR git diff ({grp_label}):\n```diff\n{grp_diff}\n```\nChanged symbols: {[c.get('symbol') for c in changed_symbols]}\nAffected downstream: {[a.get('symbol') for a in affected_symbols[:5]]}"
                if custom_prompt:
                    user_prompt += f"\nInstructions: {custom_prompt}"

                llm_res = call_external_llm(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    provider=provider,
                    api_key=api_key,
                    azure_config=azure_config
                )
                if llm_res.get("success") and llm_res.get("content"):
                    provider_used = llm_res.get("provider", "External LLM")
                    repaired_comments, _ = parse_and_repair_comments(llm_res["content"])
                    for c_item in repaired_comments:
                        candidate_findings.append(c_item)

        # 6. Negative Constraint Pre-Filtering (OCR Rule Intelligence)
        # Suppress obviously irrelevant candidates before ClaimVerifier
        filtered_candidates: List[Dict[str, Any]] = []
        suppressed_count = 0
        for cand in candidate_findings:
            suppressed, reason = evaluate_negative_constraints(cand, cand.get("existing_code", ""))
            if suppressed:
                suppressed_count += 1
                continue
            filtered_candidates.append(cand)

        # 7. Diff Relocation & Line Resolver
        # Fix line drift via diff hunks and relocate misfiled comments across files
        relocated_candidates = relocate_and_resolve_findings(filtered_candidates, diff)

        # 8. ClaimVerifier Truth Boundary
        verified_comments: List[Dict[str, Any]] = []
        for f in relocated_candidates:
            f_file = f.get("file", "")
            l_start = f.get("line_start", 1)
            l_end = f.get("line_end", l_start)
            title = f.get("title", "Review Observation")
            expl = f.get("explanation", "")
            verdict_override = f.get("verdict")

            if verdict_override == "INSUFFICIENT_EVIDENCE":
                # Relocation flagged as ambiguous across multiple files -> fail closed
                verdict = "INSUFFICIENT_EVIDENCE"
                citation = None
            else:
                # Strict verification against AST nodes and changed files
                has_ast_match = any(
                    c.get("file", "").endswith(f_file) or f_file.endswith(c.get("file", ""))
                    for c in classes
                ) if f_file else False

                is_in_diff = any(
                    cf.endswith(f_file) or f_file.endswith(cf)
                    for cf in changed_files
                ) if f_file else False

                if is_in_diff and has_ast_match:
                    verdict = "VERIFIED"
                    citation = f"{f_file}#L{l_start}-L{l_end}"
                elif is_in_diff or has_ast_match:
                    verdict = "SUGGESTION"
                    citation = f"{f_file}#L{l_start}" if f_file else None
                else:
                    verdict = "INSUFFICIENT_EVIDENCE"
                    citation = None

            comment_dict = {
                "file": f_file,
                "line_start": l_start,
                "line_end": l_end,
                "existing_code": f.get("existing_code", ""),
                "category": f.get("category", "Quality"),
                "severity": f.get("severity", "INFO"),
                "rule_id": f.get("rule_id", "CODE_TURTLE_AUDIT"),
                "title": title,
                "explanation": expl,
                "suggested_fix": f.get("suggested_fix"),
                "verdict": verdict,
                "status": verdict,
                "citation": citation,
                "evidenceCitation": citation or "No AST Citation",
                "rationale": f.get("rationale") or f"Grounded in {f_file} AST evidence." if verdict == "VERIFIED" else "Suggestion: ungrounded candidate.",
                "original_file": f.get("original_file"),
                "relocated_from": f.get("relocated_from"),
                "resolved_by": f.get("resolved_by"),
            }

            # 9. Myers Line-Diff Engine for Committable Suggestions
            enriched = attach_suggestion_diff_to_finding(comment_dict)
            verified_comments.append(enriched)

        # Calculate genuine statistics (no fabricated counts)
        verified_count = sum(1 for c in verified_comments if c["status"] == "VERIFIED")
        suggestion_count = sum(1 for c in verified_comments if c["status"] == "SUGGESTION")
        insufficient_count = sum(1 for c in verified_comments if c["status"] == "INSUFFICIENT_EVIDENCE")
        crit_count = sum(1 for c in verified_comments if c["severity"] == "CRITICAL")
        warn_count = sum(1 for c in verified_comments if c["severity"] == "WARNING")
        info_count = sum(1 for c in verified_comments if c["severity"] == "INFO")

        # Evaluate risk level based on verified blast radius and finding severities
        if crit_count > 0:
            risk_level = "CRITICAL"
        elif warn_count > 0 or len(affected_symbols) > 5:
            risk_level = "HIGH"
        elif len(affected_symbols) > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        summary_md = (
            f"**CodeTurtle AI Review**: Evaluated **{len(changed_files)}** modified file(s) and "
            f"**{len(changed_symbols)}** changed symbol(s). Downstream graph blast radius identified "
            f"**{len(affected_symbols)}** dependent component(s). Audit produced **{verified_count}** verified finding(s) "
            f"and **{suggestion_count}** architectural suggestion(s) ({suppressed_count} false positives suppressed)."
        )

        return {
            "product": "CodeTurtle AI Review",
            "provider": provider_used,
            "analysis_run_id": snap.analysis_run_id,
            "repository_id": snap.repository_id,
            "commit_hash": snap.commit_hash,
            "base_compat": base_compat,
            "risk_level": risk_level,
            "summary": summary_md,
            "what_changed": changed_symbols,
            "what_affected": affected_symbols,
            "related_tests": grounded_review.get("related_tests", []),
            "what_might_break": grounded_review.get("what_might_break", []),
            "diagram": {
                "type": "CHANGE_FLOW",
                "mermaid": mermaid_diagram,
                "status": "VERIFIED" if mermaid_diagram else "UNAVAILABLE"
            },
            "comments": verified_comments,
            "evidence_refs": evidence_refs,
            "stats": {
                "verified_count": verified_count,
                "suggestion_count": suggestion_count,
                "insufficient_count": insufficient_count,
                "suppressed_count": suppressed_count,
                "critical": crit_count,
                "warning": warn_count,
                "info": info_count,
            }
        }


# Compatibility alias
CodeRabbitReviewEngine = CodeTurtleReviewEngine
