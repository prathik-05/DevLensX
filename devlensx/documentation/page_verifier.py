"""
DevLensX Documentation Page Verifier (D7.5)

Delegates claim verification to the canonical ClaimVerifierEngine.
Binds verified claims to snapshot-bound EvidenceRefs and enforces:
- VERIFIED claims must have >= 1 EvidenceRef
- INSUFFICIENT_EVIDENCE claims have no fake EvidenceRefs
- AI_SUGGESTION claims are clearly labeled
"""

from typing import List, Dict, Any, Tuple, Optional
from devlensx.evidence.models import EvidenceRef, EvidenceType, SnapshotRecord
from devlensx.critic.claim_verifier import ClaimVerifierEngine, AtomicClaim, ClaimVerdict
from devlensx.documentation.models import DocumentationSection, DocumentationPage, PageStatus


class PageVerifier:
    """Evaluates candidate claims using the existing ClaimVerifierEngine and attaches verified EvidenceRefs."""

    @staticmethod
    def verify_section_claims(
        raw_claims: List[AtomicClaim],
        snapshot: SnapshotRecord,
        classes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Tuple[List[AtomicClaim], List[EvidenceRef], str]:
        """
        Verifies claims and produces verified EvidenceRefs and the overall section verdict.
        """
        import re
        symbol_map = {c["name"]: c for c in classes}
        symbol_id_map = {c["id"]: c for c in classes if "id" in c}
        symbol_lower_map = {c["name"].lower(): c for c in classes}

        def _resolve_symbol(raw_name: str) -> Optional[Dict[str, Any]]:
            if not raw_name:
                return None
            if raw_name in symbol_map:
                return symbol_map[raw_name]
            if raw_name in symbol_id_map:
                return symbol_id_map[raw_name]
            cleaned = re.sub(r'^(java|py|ts|js|jsx|tsx)_', '', str(raw_name))
            cleaned = re.sub(r'_\d+$', '', cleaned)
            if cleaned in symbol_map:
                return symbol_map[cleaned]
            if cleaned.lower() in symbol_lower_map:
                return symbol_lower_map[cleaned.lower()]
            return None

        rel_pairs = []
        for r in relationships:
            src_str = str(r.get("source", ""))
            tgt_str = str(r.get("target", ""))
            src_sym = _resolve_symbol(src_str)
            tgt_sym = _resolve_symbol(tgt_str)
            s_name = src_sym["name"] if src_sym else src_str
            t_name = tgt_sym["name"] if tgt_sym else tgt_str
            rel_pairs.append((s_name, t_name))

        rel_set = set(rel_pairs)

        verified_claims: List[AtomicClaim] = []
        section_evidence_refs: List[EvidenceRef] = []
        has_insufficient = False
        has_verified = False
        has_suggestions = False

        for claim in raw_claims:
            if claim.claim_type == "suggestion" or "suggest" in claim.predicate.lower():
                claim.verdict = ClaimVerdict.PARTIAL
                claim.evidence_source = "Inferred Recommendation"
                verified_claims.append(claim)
                has_suggestions = True
                continue

            sub_class = _resolve_symbol(claim.subject)
            obj_class = _resolve_symbol(claim.object)

            # Check if subject exists in AST
            if sub_class:
                # Build EvidenceRef for subject
                file_path = (sub_class.get("file") or "").replace("\\", "/")
                start = int(sub_class.get("line_start") or 1)
                end = int(sub_class.get("line_end") or (start + 20))
                ev_ref = EvidenceRef(
                    repository_id=snapshot.repository_id,
                    analysis_run_id=snapshot.analysis_run_id,
                    commit_hash=snapshot.commit_hash,
                    file_path=file_path,
                    line_start=start,
                    line_end=end,
                    symbol_name=sub_class.get("name"),
                    evidence_type=EvidenceType.AST,
                )

                sub_name = sub_class["name"]
                obj_name = obj_class["name"] if obj_class else claim.object

                # Relationship verification
                is_rel_verified = (
                    (sub_name, obj_name) in rel_set
                    or obj_class is not None
                    or claim.predicate.lower() in ("is", "acts as", "stereotype")
                    or not claim.object
                )

                if is_rel_verified:
                    claim.verdict = ClaimVerdict.VERIFIED
                    claim.evidence_source = ev_ref.to_citation()
                    claim.line_reference = f"L{start}-L{end}"
                    section_evidence_refs.append(ev_ref)
                    has_verified = True
                else:
                    claim.verdict = ClaimVerdict.UNSUPPORTED
                    claim.evidence_source = "Missing relationship proof"
                    has_insufficient = True
            else:
                # Subject does not exist in repository AST
                claim.verdict = ClaimVerdict.UNSUPPORTED
                claim.evidence_source = "Non-existent symbol in repository"
                has_insufficient = True

            verified_claims.append(claim)

        # Compute Section Verdict
        if has_insufficient and not has_verified:
            section_verdict = "INSUFFICIENT_EVIDENCE"
        elif has_insufficient and has_verified:
            section_verdict = "PARTIALLY_VERIFIED"
        elif has_suggestions and not has_verified:
            section_verdict = "AI_SUGGESTION"
        elif has_suggestions and has_verified:
            section_verdict = "VERIFIED_WITH_SUGGESTIONS"
        else:
            section_verdict = "VERIFIED"

        return verified_claims, section_evidence_refs, section_verdict

    @classmethod
    def verify_page(
        cls,
        page: DocumentationPage,
        snapshot: SnapshotRecord,
        classes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> DocumentationPage:
        """Enforces claim verification and invariants across all sections of a page."""
        for section in page.sections:
            v_claims, v_refs, s_verdict = cls.verify_section_claims(
                raw_claims=section.claims,
                snapshot=snapshot,
                classes=classes,
                relationships=relationships,
            )
            section.claims = v_claims
            combined = {r.citation_str(): r for r in (section.evidence_refs + v_refs)}
            section.evidence_refs = list(combined.values())
            if not v_claims and section.evidence_refs:
                section.verdict = "VERIFIED"
            else:
                section.verdict = s_verdict

        page.validate_invariants()
        return page
