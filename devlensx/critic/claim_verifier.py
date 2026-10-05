"""
DevLensX Claim-Level Critic Verification Engine
Parses AI response text into atomic claims (subject, predicate, object) and resolves each claim individually against AST, KuzuDB Graph, and Config evidence.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ClaimVerdict(str, Enum):
    VERIFIED = "🟢 VERIFIED"
    PARTIAL = "🔵 AI SUGGESTION"
    UNSUPPORTED = "🔴 INSUFFICIENT EVIDENCE"


@dataclass
class AtomicClaim:
    subject: str
    predicate: str
    object: str
    claim_type: str  # structural, invocation, infrastructure, endpoint
    verdict: ClaimVerdict = ClaimVerdict.UNSUPPORTED
    evidence_source: str = ""
    line_reference: Optional[str] = None


class ClaimVerifierEngine:
    @staticmethod
    def extract_and_verify_claims(ai_text: str, classes: List[Dict[str, Any]], graph_edges: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Extracts atomic claims from AI text and resolves each against AST symbols and Graph edges."""
        symbol_map = {c["name"]: c for c in classes}
        graph_edges = graph_edges or []

        # 1. Regex pattern matching structural claims: "X calls Y", "X depends on Y", "X uses Y"
        claim_pattern = re.compile(
            r'([A-Za-z0-9_]+)\s+(calls|depends on|uses|injects|extends|implements|routes to)\s+([A-Za-z0-9_]+)',
            re.IGNORECASE
        )
        matches = claim_pattern.findall(ai_text)

        verified_claims: List[AtomicClaim] = []
        unsupported_claims: List[AtomicClaim] = []
        parsed_claims: List[AtomicClaim] = []

        for sub, pred, obj in matches:
            c_type = "structural"
            if pred.lower() in ("calls", "injects"):
                c_type = "invocation"
            elif pred.lower() in ("extends", "implements"):
                c_type = "inheritance"

            claim = AtomicClaim(subject=sub, predicate=pred.lower(), object=obj, claim_type=c_type)

            # Resolve against AST symbols & Graph edges
            sub_exists = sub in symbol_map
            obj_exists = obj in symbol_map

            # Edge check. Relationship ids are synthetic (java_Name_123,
            # py_Name_1) while claims use simple names — normalize both
            # sides or real edges never match (P1-C chain fix).
            try:
                from devlensx.deep_reasoning import simple_name as _sn
            except Exception:
                def _sn(s: str) -> str:
                    return str(s or "").split(".")[-1]
            edge_exists = any(
                (_sn(e.get("source")) == sub or _sn(e.get("subject")) == sub) and
                (_sn(e.get("target")) == obj or _sn(e.get("object")) == obj)
                for e in graph_edges
            ) or (sub_exists and obj in symbol_map.get(sub, {}).get("injected_dependencies", []))

            inheritance_ok = False
            if c_type == "inheritance" and sub_exists:
                sub_cls = symbol_map[sub]
                declared = list(sub_cls.get("extends") or []) + list(sub_cls.get("implements") or [])
                declared += list((sub_cls.get("metadata") or {}).get("extends") or [])
                declared += list((sub_cls.get("metadata") or {}).get("implements") or [])
                declared_names = {str(d).split(".")[-1] for d in declared if d}
                if obj in declared_names:
                    inheritance_ok = True
                else:
                    inheritance_ok = any(
                        (e.get("source") == sub or e.get("subject") == sub)
                        and str(e.get("type", "")).upper() in ("EXTENDS", "IMPLEMENTS", "INHERITS")
                        and (e.get("target") == obj or e.get("object") == obj)
                        for e in graph_edges
                    )

            if sub_exists and obj_exists and (edge_exists or inheritance_ok):
                claim.verdict = ClaimVerdict.VERIFIED
                sub_file = symbol_map[sub].get("file", f"{sub}.java")
                sub_line = symbol_map[sub].get("line_start", 1)
                claim.evidence_source = f"AST + Kuzu Graph ({sub_file}#L{sub_line})"
                claim.line_reference = f"{sub_file}#L{sub_line}"
                verified_claims.append(claim)
            elif sub_exists or obj_exists:
                claim.verdict = ClaimVerdict.PARTIAL
                claim.evidence_source = "Partial AST symbol match"
                unsupported_claims.append(claim)
            else:
                claim.verdict = ClaimVerdict.UNSUPPORTED
                claim.evidence_source = "No AST symbol or graph edge found in repository"
                unsupported_claims.append(claim)

            parsed_claims.append(claim)

        # Also check for ungrounded tech stack claims (e.g. Redis, Kafka)
        tech_keywords = ["redis", "kafka", "rabbitmq", "elasticsearch", "mongodb", "neo4j"]
        text_lower = ai_text.lower()
        for kw in tech_keywords:
            if kw in text_lower:
                # Check class names, file paths, imports, injected deps, and metadata
                def _mentions_tech(c):
                    blob = " ".join([
                        str(c.get("name", "")), str(c.get("file", "")),
                        str(c.get("file_imports", "")), str(c.get("injected_dependencies", "")),
                        str((c.get("metadata") or {}).get("injected_dependencies", "")),
                        str(c.get("annotations", "")),
                    ]).lower()
                    return kw in blob
                kw_found = any(_mentions_tech(c) for c in classes)
                if not kw_found:
                    unsupported_claims.append(AtomicClaim(
                        subject=kw.capitalize(),
                        predicate="manages",
                        object="data",
                        claim_type="infrastructure",
                        verdict=ClaimVerdict.UNSUPPORTED,
                        evidence_source=f"No repository evidence confirms {kw.capitalize()} is used."
                    ))

        return {
            "total_claims_analyzed": len(parsed_claims) + sum(
                1 for c in unsupported_claims if c not in parsed_claims
            ),
            "verified_claims_count": len(verified_claims),
            "unsupported_claims_count": len(unsupported_claims),
            "verified_claims": [
                {
                    "subject": c.subject,
                    "predicate": c.predicate,
                    "object": c.object,
                    "verdict": c.verdict.value,
                    "evidence": c.evidence_source,
                    "line_reference": c.line_reference
                }
                for c in verified_claims
            ],
            "unsupported_claims": [
                {
                    "subject": c.subject,
                    "predicate": c.predicate,
                    "object": c.object,
                    "verdict": c.verdict.value,
                    "evidence": c.evidence_source
                }
                for c in unsupported_claims
            ]
        }
