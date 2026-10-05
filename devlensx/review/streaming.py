"""P1-E verified streaming orchestration.

Central invariant: NO LLM-generated finding reaches the client until it has
passed through ClaimVerifier. The token stream fills a server-side candidate
buffer; completed candidates are verified, then emitted as typed events.
Progress/status events stream freely — findings do not.

Event lifecycle (in order):
  review_started -> snapshot_validated -> diff_parsed -> symbols_resolved
  -> impact_resolved -> (candidate_found -> claim_verification_started
  -> finding_verified | finding_suggestion | finding_insufficient)*
  -> review_summary -> review_complete
"""

from __future__ import annotations

import re
from typing import Any, AsyncGenerator, Dict, List, Optional

_CANDIDATE_HEADER_RE = re.compile(r"^###\s+(.*)$")


def split_candidates(buffer: str) -> tuple:
    """Split buffered text into (complete_candidates, remainder).

    A candidate is complete once the NEXT '### ' header starts. The trailing
    chunk stays in the buffer until the stream ends (then it flushes as one
    final candidate, even without a header).
    """
    lines = buffer.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if _CANDIDATE_HEADER_RE.match(ln.strip())]
    if len(starts) < 2:
        return [], buffer
    complete = "".join(lines[starts[0]:starts[1]]).strip()
    rest = "".join(lines[starts[1]:])
    more, remainder = split_candidates(rest)
    return [complete] + more, remainder


def _finalize_event(finding: Dict[str, Any], index: int) -> Dict[str, Any]:
    verdict = finding.get("verdict", "NOT_VERIFIED")
    if verdict == "VERIFIED":
        etype = "finding_verified"
    elif verdict in ("AI_SUGGESTION", "SUGGESTION"):
        etype = "finding_suggestion"
    else:
        etype = "finding_insufficient"
    return {"type": etype, "index": index, "finding": finding}


async def stream_review(
    engine: Any,
    diff: str,
    context: Optional[Dict[str, Any]] = None,
    snapshot: Optional[Dict[str, Any]] = None,
    base_commit: Optional[str] = None,
    trace: Any = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Emit the verified event lifecycle for a diff review.

    P1-G: when a trace is supplied, every lifecycle transition is also
    recorded as a sanitized D10 observability event (counts/ids/timings
    only — never finding text, diffs, or prompts).
    """
    from devlensx.codereview import (
        validate_diff_size, scan_and_redact_diff, DIFF_TOO_LARGE,
        VERDICT_VERIFIED, VERDICT_SUGGESTION,
    )
    from devlensx.review.grounding import ground_diff

    ctx = context or {}
    snap = snapshot or {}
    provider_name = getattr(getattr(engine, "config", None), "provider", "unknown")
    t = trace
    if t is not None:
        t.mark("start")
        t.count("input_chars", len(diff))
        t.count("input_lines", diff.count("\n") + 1)
        t.event("review_started", status="started")
    yield {"type": "review_started", "provider": provider_name}
    yield {"type": "snapshot_validated", "bound": bool(snap.get("analysis_run_id")),
           "snapshot": {k: snap.get(k) for k in ("repository_id", "analysis_run_id", "commit_hash")}}

    try:
        validate_diff_size(diff)
    except ValueError as e:
        yield {"type": "review_complete", "status": "rejected",
               "detail": str(e), "fallback_used": False}
        return

    safe_diff, secrets_found, secret_kinds = scan_and_redact_diff(diff)
    model = {"classes": ctx.get("classes", []), "relationships": ctx.get("relationships", [])}
    grounding = ground_diff(safe_diff, model, snap, base_commit)
    if t is not None:
        t.event("snapshot_validated",
                status="ok" if snap.get("analysis_run_id") else "unbound")
        t.event("diff_parsed", counts={"files": grounding.summary.get("files", 0),
                                       "hunks": grounding.summary.get("hunks", 0)})
        t.event("symbols_resolved", counts={"changed_symbols": len(grounding.changed)})
        t.event("impact_resolved", counts={"affected_symbols": len(grounding.affected)})
    yield {"type": "diff_parsed", "summary": grounding.summary}
    yield {"type": "symbols_resolved",
           "changed": [c.to_dict() for c in grounding.changed]}
    yield {"type": "impact_resolved",
           "affected": len(grounding.affected),
           "tests": sorted({a["target_symbol"] for a in grounding.affected
                            if a.get("relationship") == "TESTS"}),
           "base_compat": grounding.base_compat}

    counts = {"VERIFIED": 0, "SUGGESTION": 0, "INSUFFICIENT": 0}
    seen_fingerprints: set = set()
    index = 0
    fallback_used = False
    from devlensx.codereview import finding_fingerprint as _fingerprint

    def _count(f: Dict[str, Any]) -> None:
        v = f.get("verdict", "NOT_VERIFIED")
        if v == VERDICT_VERIFIED:
            counts["VERIFIED"] += 1
        elif v in (VERDICT_SUGGESTION, "SUGGESTION"):
            counts["SUGGESTION"] += 1
        else:
            counts["INSUFFICIENT"] += 1

    def _seen(f: Dict[str, Any]) -> bool:
        # P1-F: fingerprint identity (snapshot+symbol+lines+category+claim),
        # never title alone — same title on two files/lines are two findings.
        fp = _fingerprint(f, snap if snap.get("analysis_run_id") else None)
        if fp in seen_fingerprints:
            return True
        seen_fingerprints.add(fp)
        return False

    async def _emit_finalized(candidates: List[str]) -> None:
        nonlocal index
        for cand in candidates:
            parsed = engine._parse_findings(cand)
            if not parsed:
                continue
            cid = f"c{index}"
            # P1-F: candidate_found carries an opaque id ONLY — no title,
            # severity, or claim. A client must not render it as a finding.
            yield {"type": "candidate_found", "index": index, "candidate_id": cid}
            if t is not None:
                t.event("candidate_found", extra={"candidate_id": cid, "index": index})
                t.mark("verification_start")
            yield {"type": "claim_verification_started", "index": index,
                   "candidate_id": cid}
            final = engine._finalize(parsed, ctx, snap if snap.get("analysis_run_id") else None, diff)
            if t is not None:
                t.mark("verification_end")
            for f in final:
                if _seen(f):
                    continue
                _count(f)
                if t is not None:
                    v = f.get("verdict", "NOT_VERIFIED")
                    et = {"VERIFIED": "finding_verified"}.get(v, "finding_insufficient")
                    if v in (VERDICT_SUGGESTION, "SUGGESTION"):
                        et = "finding_suggestion"
                    t.event(et, extra={"candidate_id": cid, "index": index})
                yield _finalize_event(f, index)
            index += 1

    async def _emit_preverified(findings: List[Dict[str, Any]]) -> None:
        """Already-finalized findings (offline path): emitted with their
        verdicts intact — never re-parsed as text (that would drop evidence)."""
        nonlocal index
        for f in findings:
            if _seen(f):
                continue
            _count(f)
            yield _finalize_event(f, index)
            index += 1

    provider = None
    try:
        if engine.config.is_configured():
            provider = engine._gateway_provider()
    except Exception:
        provider = None

    use_llm = bool(provider is not None and provider.capabilities().get("llm", True))
    if t is not None:
        t.count("files", grounding.summary.get("files", 0))
        t.count("hunks", grounding.summary.get("hunks", 0))
        t.count("changed_symbols", len(grounding.changed))
        t.count("affected_symbols", len(grounding.affected))
        t.set_flag("base_compat", grounding.base_compat.get("status"))
        t.set_flag("secrets_detected", secrets_found)
    if not use_llm:
        result = engine._mock_review(diff, context=ctx, snapshot=snap or None)
        async for ev in _emit_preverified(result.findings):
            yield ev
        if t is not None:
            t.count("findings_total", sum(counts.values()))
            t.set_flag("fallback_used", True)
            t.event("review_complete", status="complete", counts=dict(counts),
                    extra={"fallback_used": True})
            t.metric("review_duration", t.summary()["total_duration_ms"] or 0.0,
                     extra={"fallback_used": True})
        yield {"type": "review_summary", "counts": counts,
               "base_compat": grounding.base_compat,
               "secrets_detected": secrets_found, "fallback_used": True}
        yield {"type": "review_complete", "status": "complete", "fallback_used": True}
        return

    # Live path: buffer tokens, verify per completed candidate.
    user_content = engine.build_user_message(safe_diff)
    buffer = ""
    truncated = False
    first_token = False
    try:
        if t is not None:
            t.mark("provider_start")
            t.event("provider_started", status="started")
        async for chunk in provider.astream(
            user_content, engine.DEFAULT_SYSTEM_PROMPT,
            temperature=engine.config.temperature, max_tokens=engine.config.max_tokens,
        ):
            if not chunk:
                continue
            if not first_token:
                first_token = True
                if t is not None:
                    t.mark("provider_first_token")
                    t.event("provider_first_token", status="ok")
            buffer += chunk
            complete, buffer = split_candidates(buffer)
            async for ev in _emit_finalized(complete):
                yield ev
        if t is not None:
            t.mark("provider_end")
    except Exception as e:  # provider failure mid-stream -> deterministic fallback
        from devlensx.review.telemetry import classify_provider_failure
        fallback_used = True
        failure = classify_provider_failure(e)
        if t is not None:
            t.mark("provider_end")
            t.event("provider_failed", status="failed", error_code=failure["category"],
                    extra={"http_status": failure.get("http_status")})
            t.event("fallback_started", status="started")
        result = engine._mock_review(diff, context=ctx, snapshot=snap or None,
                                     error=f"stream interrupted: {type(e).__name__}")
        async for ev in _emit_preverified(result.findings):
            yield ev
        truncated = True

    # Flush remainder as one final candidate (malformed tail included).
    if buffer.strip():
        async for ev in _emit_finalized([buffer.strip()]):
            yield ev

    if t is not None:
        t.count("findings_total", sum(counts.values()))
        t.set_flag("fallback_used", fallback_used)
        t.set_flag("stream_truncated", truncated)
        summary = t.summary()
        t.event("review_complete", status="complete", counts=dict(counts),
                extra={"fallback_used": fallback_used, "stream_truncated": truncated})
        t.metric("review_duration", summary["total_duration_ms"] or 0.0)
    yield {"type": "review_summary", "counts": counts,
           "base_compat": grounding.base_compat,
           "secrets_detected": secrets_found, "fallback_used": fallback_used,
           "telemetry": t.summary() if t is not None else None}
    yield {"type": "review_complete", "status": "complete",
           "truncated": truncated, "fallback_used": fallback_used}
