"""Build validation — ensures no proposed change masquerades as verified."""

def validate_change_plan(plan) -> bool:
    for step in plan.steps:
        if step.status == "VERIFIED_FACT":
            assert step.evidence_ref is not None, f"VERIFIED step {step.symbol} must have EvidenceRef"
        if step.status == "AI_SUGGESTION":
            # suggestions must not claim to be existing code
            assert step.verification_required is True
    return True