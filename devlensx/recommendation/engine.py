"""
DevLensX Recommendation Engine & Repository Intelligence Score Synthesizer

Synthesizes verified findings from the Critic Agent into prioritized action cards
and computes the overall Repository Intelligence Score (0–100) using the locked 5-weighted formula:
  - Architecture: 30%
  - Security: 25%
  - Maintainability: 20%
  - Coupling: 15%
  - Evidence Coverage: 10%
"""

from devlensx.config import SCORE_WEIGHTS


class RecommendationEngine:
    @staticmethod
    def _is_verified(f):
        # Accept plain Critic verdicts and emoji-prefixed ClaimVerifier verdicts.
        verdict = str(f.get("verdict", ""))
        return verdict == "VERIFIED" or verdict.endswith("VERIFIED")

    def synthesize(self, verified_findings, repo_model):
        """Synthesizes verified findings into prioritized cards and overall score."""
        verified = [f for f in verified_findings if self._is_verified(f)]
        rejected = [f for f in verified_findings
                    if f.get("verdict") == "REJECTED" or str(f.get("verdict", "")).endswith("REJECTED")]

        # Calculate Sub-scores
        maint_penalties = sum(1 for f in verified if f["category"] == "Maintainability")
        maintainability_score = max(0, 100 - (maint_penalties * 15))

        high_couplings = sum(1 for f in verified if f["category"] == "Coupling")
        coupling_score = max(0, 100 - (high_couplings * 10))

        architecture_score = int((maintainability_score + coupling_score) / 2)

        sec_high = sum(1 for f in verified if f["category"] in ("Hardcoded Secret", "API Security") and f["severity"] == "HIGH")
        sec_med = sum(1 for f in verified if f["category"] in ("Hardcoded Secret", "API Security") and f["severity"] == "MEDIUM")
        security_score = max(0, 100 - (sec_high * 20 + sec_med * 10))

        files_parsed = repo_model.get("stats", {}).get("files_parsed", 0)
        repo_lang = repo_model.get("repo_summary", {}).get("language", "Unknown")
        parsed_symbols = len(repo_model.get("classes", []) or [])

        if files_parsed == 0 and parsed_symbols == 0:
            maintainability_score = 0
            coupling_score = 0
            architecture_score = 0
            security_score = 0
            evidence_coverage_score = 0.0
            overall_score = 0.0
        else:
            if verified:
                scores = [f.get("evidence_coverage_score", 0.0) for f in verified]
                evidence_coverage_score = round(sum(scores) / len(scores), 1)
            elif rejected:
                # Every claim failed grounding: coverage is zero, not perfect.
                evidence_coverage_score = 0.0
            else:
                evidence_coverage_score = 100.0

            # Weighted Overall Score (Locked 5-Weighted Formula)
            overall_score = round(
                (architecture_score * SCORE_WEIGHTS["architecture"]) +
                (security_score * SCORE_WEIGHTS["security"]) +
                (maintainability_score * SCORE_WEIGHTS["maintainability"]) +
                (coupling_score * SCORE_WEIGHTS["coupling"]) +
                (evidence_coverage_score * SCORE_WEIGHTS["evidence_coverage"]),
                1
            )

        if files_parsed == 0 and parsed_symbols == 0:
            sub_score_explanations = {
                "architecture": f"0% score: No source files parsed (Primary language detected: {repo_lang}).",
                "security": f"0% score: No source files parsed for security analysis.",
                "maintainability": f"0% score: No source files found.",
                "coupling": f"0% score: Knowledge Graph empty, nothing parsed.",
                "evidence_coverage": f"0% score: No repository content to verify."
            }
        else:
            sub_score_explanations = {
                "architecture": f"30% weight: Average of Maintainability ({maintainability_score}) and Coupling ({coupling_score}).",
                "security": f"25% weight: 100 minus penalties for {sec_high} high and {sec_med} medium security issues.",
                "maintainability": f"20% weight: 100 minus 15 points per god class (>15 methods). Found {maint_penalties}.",
                "coupling": f"15% weight: 100 minus 10 points per high blast radius component. Found {high_couplings}.",
                "evidence_coverage": f"10% weight: Average Evidence Coverage Score across verified findings ({evidence_coverage_score}%)."
            }

        # Build Recommendation Cards
        recommendation_cards = []
        for idx, item in enumerate(verified[:5], 1):
            evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
            affected = [item.get("class_name", "")]
            affected += [c for c in evidence.get("affected_controllers", []) or [] if c not in affected]
            affected += [t for t in evidence.get("affected_tests", []) or [] if t not in affected]
            sev = item.get("severity", "MEDIUM")
            recommendation_cards.append({
                "rank": idx,
                "title": item.get("title", ""),
                "target_component": item.get("class_name", ""),
                "file": item.get("file", ""),
                "priority": sev,
                "reason": item.get("claim", ""),
                "evidence_summary": item.get("evidence_ratio", ""),
                "affected_components": affected,
                "estimated_effort": "HIGH" if sev == "HIGH" else ("MEDIUM" if sev == "MEDIUM" else "LOW"),
                "expected_benefit": "Immediate security vulnerability remediation" if "Secret" in item.get("category", "") else "High structural risk reduction",
                "evidence_coverage_score": item.get("evidence_coverage_score", 0.0),
                "evidence_trail": item.get("evidence_trail", {})
            })

        return {
            "repository_intelligence_score": {
                "overall": overall_score,
                "sub_scores": {
                    "architecture": architecture_score,
                    "security": security_score,
                    "maintainability": maintainability_score,
                    "coupling": coupling_score,
                    "evidence_coverage": evidence_coverage_score
                },
                "sub_score_explanations": sub_score_explanations,
                "score_weights_configured": SCORE_WEIGHTS
            },
            "top_engineering_recommendations": recommendation_cards,
            "total_verified_findings": len(verified),
            "total_rejected_findings": len(rejected),
            "rejected_findings_sample": rejected
        }
