"""
DevLensX Atomic Claim Extractor (D7.4)

Extracts candidate atomic claims (subject, predicate, object) from generated prose or structured JSON.
IMPORTANT INVARIANT: ClaimExtractor DOES NOT verify anything.
Verification is exclusively performed by the existing ClaimVerifierEngine in page_verifier.py.
"""

import re
from typing import List, Dict, Any
from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict


class ClaimExtractor:
    """Extracts candidate claims from text or structured schemas without performing verification."""

    # Matches factual assertions: "X calls Y", "X depends on Y", "X uses Y", "X extends Y", "X handles Y"
    CLAIM_PATTERN = re.compile(
        r'[`"]?([A-Za-z0-9_]+)[`"]?\s+(calls|depends on|depends_on|uses|injects|extends|implements|routes to|routes_to|delegates to|delegates_to|persists|manages|provides|imports|has structure|has_structure|architecture|layer)\s+[`"]?([A-Za-z0-9_./@-]+)[`"]?',
        re.IGNORECASE
    )

    # Matches definition and location assertions: "X is defined in Y", "X defined in Y", "X located in Y"
    DEFINITION_PATTERN = re.compile(
        r'[`"]?([A-Za-z0-9_]+)[`"]?\s+(?:is\s+)?(defined in|defined_in|located in)\s+[`"]?([A-Za-z0-9_./@-]+)[`"]?',
        re.IGNORECASE
    )

    # Matches AI suggestion / recommendation assertions: "Consider adding X", "X may benefit from Y"
    SUGGESTION_PATTERN = re.compile(
        r'(?:consider|recommend|may benefit from|could introduce|suggests)\s+([A-Za-z0-9_\s]{3,40})',
        re.IGNORECASE
    )

    # Matches absent / negative assertions: "No evidence was found for X", "No implementation for X"
    NEGATIVE_PATTERN = re.compile(
        r'(?:no evidence was found for|no implementation for|lacks evidence for|not found for|no evidence for)\s+([A-Za-z0-9_]+)',
        re.IGNORECASE
    )

    @classmethod
    def extract_from_text(cls, text: str) -> List[AtomicClaim]:
        """Extracts candidate claims from raw prose text."""
        claims: List[AtomicClaim] = []
        if not text:
            return claims

        # Strip markdown formatting markers so regex matches clean tokens
        clean_text = re.sub(r'[*`"]', '', text)

        # 1. Structural / Relationship assertions
        matches = cls.CLAIM_PATTERN.findall(clean_text)
        for sub, pred, obj in matches:
            if sub.lower() in ("is", "the", "this", "that", "it"):
                continue
            c_type = "structural"
            pred_norm = pred.lower()
            if pred_norm in ("calls", "injects", "delegates to"):
                c_type = "invocation"
            elif pred_norm in ("extends", "implements"):
                c_type = "inheritance"
            elif pred_norm in ("routes to", "manages"):
                c_type = "endpoint"
            elif pred_norm in ("layer", "architecture"):
                c_type = "architecture"
            elif pred_norm in ("provides", "has structure", "has_structure"):
                c_type = "structure"

            claims.append(AtomicClaim(
                subject=sub.strip(),
                predicate=pred_norm,
                object=obj.strip().rstrip(".,;:)'\""),
                claim_type=c_type,
                verdict=ClaimVerdict.UNSUPPORTED,  # Unverified candidate
            ))

        # 2. Definition assertions
        def_matches = cls.DEFINITION_PATTERN.findall(clean_text)
        for sub, pred, obj in def_matches:
            if sub.lower() in ("is", "the", "this", "that", "it"):
                continue
            claims.append(AtomicClaim(
                subject=sub.strip(),
                predicate="defined in",
                object=obj.strip().rstrip(".,;:)'\""),
                claim_type="definition",
                verdict=ClaimVerdict.UNSUPPORTED,
            ))

        # 2. Recommendation / Suggestion assertions
        sug_matches = cls.SUGGESTION_PATTERN.findall(text)
        for sug in sug_matches:
            sug_clean = sug.strip()
            if sug_clean:
                claims.append(AtomicClaim(
                    subject="System",
                    predicate="suggests",
                    object=sug_clean,
                    claim_type="suggestion",
                    verdict=ClaimVerdict.PARTIAL,  # Explicit AI_SUGGESTION
                ))

        # 3. Absent / Negative capability assertions
        neg_matches = cls.NEGATIVE_PATTERN.findall(clean_text)
        for target_tech in neg_matches:
            target_clean = target_tech.strip()
            if target_clean and target_clean.lower() not in ("is", "the", "this", "that"):
                claims.append(AtomicClaim(
                    subject="Repository",
                    predicate="lacks",
                    object=target_clean,
                    claim_type="negative",
                    verdict=ClaimVerdict.UNSUPPORTED,
                ))

        return claims

    @classmethod
    def extract_from_structured_dict(cls, section_dict: Dict[str, Any]) -> List[AtomicClaim]:
        """Extracts claims from explicitly structured section dicts with fallback to content parsing."""
        claims: List[AtomicClaim] = []
        raw_claims = section_dict.get("claims", [])
        content = section_dict.get("content", "")

        for c in raw_claims:
            if isinstance(c, dict):
                sub = c.get("subject", "")
                pred = c.get("predicate", "depends on")
                obj = c.get("object", "")
                c_type = c.get("claim_type", "structural")
                is_sug = c.get("is_suggestion", False) or "suggest" in pred.lower()

                claims.append(AtomicClaim(
                    subject=sub,
                    predicate=pred,
                    object=obj,
                    claim_type=c_type,
                    verdict=ClaimVerdict.PARTIAL if is_sug else ClaimVerdict.UNSUPPORTED,
                ))

        # Also extract from prose if raw_claims was empty
        if not claims and content:
            claims.extend(cls.extract_from_text(content))

        return claims
