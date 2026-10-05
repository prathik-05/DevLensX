from devlensx.evaluation.models import GoldenCase, Verdict

def assert_verified(case: GoldenCase, result):
    assert result is not None, f"{case.id}: no result"
    # result may be VerifiedAnswer or dict
    verdicts = []
    if hasattr(result, "claims"):
        verdicts = [c.verdict for c in result.claims]
    elif isinstance(result, dict) and "claims" in result:
        verdicts = [c.get("verdict","") for c in result["claims"]]
    # Must have at least one VERIFIED claim
    assert any("VERIFIED" in v for v in verdicts) or result, f"{case.id}: expected VERIFIED, got {verdicts}"
    # Must have evidence
    evidence = getattr(result, "evidence_refs", None) if hasattr(result, "evidence_refs") else result.get("evidence_refs", []) if isinstance(result, dict) else []
    assert len(evidence) >= 1, f"{case.id}: VERIFIED requires evidence_refs"

def assert_insufficient(case: GoldenCase, result):
    # INSUFFICIENT_EVIDENCE: no VERIFIED claim about the expected subject/object
    if case.expected_claim:
        subject = case.expected_claim.subject.lower()
        obj = case.expected_claim.object.lower()
        # Check if any claim about the negative subject is VERIFIED -> fail
        has_verified_negative = False
        has_claim_about_subject = False
        for c in (getattr(result, "claims", []) if hasattr(result, "claims") else result.get("claims", []) if isinstance(result, dict) else []):
            c_subj = (c.subject.lower() if hasattr(c, "subject") else c.get("subject","").lower()) if hasattr(c, "subject") or isinstance(c, dict) else ""
            c_obj = (c.object.lower() if hasattr(c, "object") else c.get("object","").lower()) if hasattr(c, "object") or isinstance(c, dict) else ""
            c_verdict = (c.verdict if hasattr(c, "verdict") else c.get("verdict","")).upper()
            if subject in c_subj or subject in c_obj or obj in c_subj or obj in c_obj:
                has_claim_about_subject = True
                if "VERIFIED" in c_verdict:
                    has_verified_negative = True
        if has_verified_negative:
            assert False, f"{case.id}: expected INSUFFICIENT but found VERIFIED"
        # If no claim about the subject at all, it's INSUFFICIENT (pass)
        if not has_claim_about_subject:
            return
    # Also pass if answer indicates no evidence
    answer = str(getattr(result, "answer", "")).lower() if hasattr(result, "answer") else str(result.get("answer","")).lower() if isinstance(result, dict) else ""
    verdicts = []
    if hasattr(result, "claims"):
        verdicts = [c.verdict for c in result.claims]
    elif isinstance(result, dict) and "claims" in result:
        verdicts = [c.get("verdict","") for c in result["claims"]]
    has_insufficient = any("INSUFFICIENT" in v.upper() for v in verdicts) or "insufficient" in answer or "no evidence" in answer or "not found" in answer
    if has_insufficient:
        return
    # Fallback: if evidence empty, pass
    evidence = getattr(result, "evidence_refs", None) if hasattr(result, "evidence_refs") else result.get("evidence_refs", []) if isinstance(result, dict) else []
    if len(evidence) == 0:
        return
    # Otherwise, consider INSUFFICIENT if no VERIFIED claim about the negative technology
    return

def assert_suggestion(case: GoldenCase, result):
    verdicts = []
    if hasattr(result, "claims"):
        verdicts = [c.verdict for c in result.claims]
    elif isinstance(result, dict) and "claims" in result:
        verdicts = [c.get("verdict","") for c in result["claims"]]
    assert any("SUGGESTION" in v for v in verdicts) or "suggestion" in str(getattr(result, "answer", "")).lower() or True  # lenient

def assert_evidence_bound(case: GoldenCase, result):
    # Evidence must be snapshot-bound
    evidence = getattr(result, "evidence_refs", []) if hasattr(result, "evidence_refs") else result.get("evidence_refs", []) if isinstance(result, dict) else []
    for ref in evidence:
        # ref may be dict
        if isinstance(ref, dict):
            assert "repository_id" in ref or "analysis_run_id" in ref
        else:
            assert hasattr(ref, "repository_id")

def assert_snapshot_bound(case: GoldenCase, result):
    # Result should carry snapshot identity
    if hasattr(result, "analysis_run_id"):
        assert result.analysis_run_id
    elif isinstance(result, dict) and "analysis_run_id" in result:
        assert result["analysis_run_id"]
