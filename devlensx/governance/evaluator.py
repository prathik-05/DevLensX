"""
DevLensX Architectural Governance Evaluator (Phase P5-A)

Evaluates architectural rules against an immutable repository snapshot
and passes candidates strictly through the Evidence Resolver to determine
official verification verdicts.

CRITICAL INVARIANTS:
1. Truth boundary:
   GovernanceEvaluator NEVER self-assigns VERIFIED.
   A VERIFIED finding requires an EvidenceRef that resolves cleanly against
   the registered snapshot via EvidenceResolver.
2. Severity is completely independent of verification status.
3. Snapshot isolation is maintained via (repository_id, analysis_run_id, commit_hash).
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple

from devlensx.governance.models import (
    ArchitecturalRule,
    CandidateViolation,
    GovernanceFinding,
    CycleType,
)
from devlensx.governance.rules import matches_selector, get_governance_rule_registry
from devlensx.governance.cycles import (
    detect_import_cycles,
    detect_inheritance_cycles,
    detect_call_graph_cycles,
)
from devlensx.evidence.models import EvidenceRef, EvidenceType, ResolutionStatus
from devlensx.evidence.resolver import get_snapshot_registry, EvidenceResolver, SnapshotRegistry


class GovernanceEvaluator:
    """
    Evaluates declarative architectural governance rules against snapshots.
    """

    def __init__(
        self,
        snapshot_registry: Optional[SnapshotRegistry] = None,
        evidence_resolver: Optional[EvidenceResolver] = None,
    ):
        self._snapshot_registry = snapshot_registry
        self._evidence_resolver = evidence_resolver

    @property
    def snapshot_registry(self) -> SnapshotRegistry:
        return self._snapshot_registry or get_snapshot_registry()

    @property
    def evidence_resolver(self) -> EvidenceResolver:
        return self._evidence_resolver or EvidenceResolver(self.snapshot_registry)

    def evaluate(
        self,
        repository_id: str,
        analysis_run_id: str,
        commit_hash: Optional[str] = None,
        rules: Optional[List[ArchitecturalRule]] = None,
        classes: Optional[List[Dict[str, Any]]] = None,
        graph_edges: Optional[List[Dict[str, Any]]] = None,
        file_imports: Optional[Dict[str, List[str]]] = None,
    ) -> List[GovernanceFinding]:
        """
        Main entrypoint:
        1. Loads model data for snapshot if not supplied.
        2. Generates CandidateViolations by evaluating rules.
        3. Validates CandidateViolations through EvidenceResolver.
        4. Emits GovernanceFindings with official verdicts.
        """
        if classes is None or graph_edges is None:
            try:
                from devlensx.chat.orchestrator import _load_model
                model = _load_model(analysis_run_id)
                if classes is None:
                    classes = model.get("classes", [])
                if graph_edges is None:
                    graph_edges = model.get("graph_edges", [])
            except Exception:
                classes = classes or []
                graph_edges = graph_edges or []

        if rules is None:
            rules = get_governance_rule_registry().get_rules(enabled_only=True)

        candidates = self.generate_candidate_violations(
            repository_id=repository_id,
            analysis_run_id=analysis_run_id,
            commit_hash=commit_hash,
            rules=rules,
            classes=classes,
            graph_edges=graph_edges,
            file_imports=file_imports,
        )

        return self.verify_candidates(candidates)

    def generate_candidate_violations(
        self,
        repository_id: str,
        analysis_run_id: str,
        commit_hash: Optional[str],
        rules: List[ArchitecturalRule],
        classes: List[Dict[str, Any]],
        graph_edges: List[Dict[str, Any]],
        file_imports: Optional[Dict[str, List[str]]] = None,
    ) -> List[CandidateViolation]:
        """
        Emits unverified candidate violations based on structural rule evaluation.
        """
        candidates: List[CandidateViolation] = []
        symbol_map: Dict[str, Dict[str, Any]] = {c.get("name", ""): c for c in classes if c.get("name")}
        if rules is None:
            rules = get_governance_rule_registry().get_rules(enabled_only=True)
        snapshot_identity = (repository_id, analysis_run_id, commit_hash)

        for rule in rules:
            if not rule.enabled:
                continue

            if rule.rule_type in ("LAYER_HIERARCHY", "FORBIDDEN_DEPENDENCY"):
                candidates.extend(
                    self._evaluate_dependency_rule(
                        rule=rule,
                        classes=classes,
                        symbol_map=symbol_map,
                        graph_edges=graph_edges,
                        snapshot_identity=snapshot_identity,
                    )
                )

            elif rule.rule_type == "CYCLE_DETECTION":
                cycle_scope = (rule.scope or {}).get("cycle_type")
                if cycle_scope == CycleType.IMPORT_CYCLE.value:
                    candidates.extend(detect_import_cycles(classes, snapshot_identity, file_imports))
                elif cycle_scope == CycleType.INHERITANCE_CYCLE.value:
                    candidates.extend(detect_inheritance_cycles(classes, snapshot_identity, graph_edges))
                elif cycle_scope == CycleType.CALL_GRAPH_CYCLE.value:
                    candidates.extend(detect_call_graph_cycles(classes, snapshot_identity, graph_edges))
                else:
                    # Run all three
                    candidates.extend(detect_import_cycles(classes, snapshot_identity, file_imports))
                    candidates.extend(detect_inheritance_cycles(classes, snapshot_identity, graph_edges))
                    candidates.extend(detect_call_graph_cycles(classes, snapshot_identity, graph_edges))

            elif rule.rule_type == "REQUIRED_ANNOTATION":
                candidates.extend(
                    self._evaluate_required_annotation_rule(
                        rule=rule,
                        classes=classes,
                        snapshot_identity=snapshot_identity,
                    )
                )

        return candidates

    def _evaluate_dependency_rule(
        self,
        rule: ArchitecturalRule,
        classes: List[Dict[str, Any]],
        symbol_map: Dict[str, Dict[str, Any]],
        graph_edges: List[Dict[str, Any]],
        snapshot_identity: Tuple[str, str, Optional[str]],
    ) -> List[CandidateViolation]:
        repo_id, run_id, commit_hash = snapshot_identity
        violations: List[CandidateViolation] = []

        for src_cls in classes:
            if not matches_selector(src_cls, rule.source_selector):
                continue

            src_name = src_cls.get("name", "")
            fpath = src_cls.get("file") or src_cls.get("file_path") or f"{src_name}.java"
            lstart = int(src_cls.get("line_start") or 1)
            lend = int(src_cls.get("line_end") or lstart + 10)

            # Collect all target names referenced by src_cls
            target_candidates: List[Tuple[str, str]] = []  # (target_name, ref_source)

            # 1. Injected dependencies
            for dep in src_cls.get("injected_dependencies", []):
                d_name = str(dep).split(".")[-1]
                target_candidates.append((d_name, "injected_dependency"))

            # 2. Graph edges
            for edge in graph_edges:
                edge_src = str(edge.get("source") or edge.get("subject") or "").split(".")[-1]
                if edge_src == src_name:
                    edge_tgt = str(edge.get("target") or edge.get("object") or "").split(".")[-1]
                    target_candidates.append((edge_tgt, "graph_edge"))

            # 3. Imports
            imports = src_cls.get("imports") or (src_cls.get("metadata") or {}).get("imports") or []
            for imp in imports:
                i_name = str(imp).split(".")[-1]
                target_candidates.append((i_name, "import"))

            for tgt_name, ref_kind in target_candidates:
                tgt_cls = symbol_map.get(tgt_name)
                if not tgt_cls:
                    continue

                if matches_selector(tgt_cls, rule.target_selector):
                    if rule.constraint == "FORBIDDEN":
                        evidence_ref = EvidenceRef(
                            repository_id=repo_id,
                            analysis_run_id=run_id,
                            commit_hash=commit_hash,
                            file_path=fpath,
                            line_start=lstart,
                            line_end=lend,
                            symbol_name=src_name,
                            evidence_type=EvidenceType.AST,
                        )

                        violations.append(CandidateViolation(
                            rule_id=rule.rule_id,
                            violation_type=rule.rule_type,
                            severity=rule.severity,
                            source_symbol=src_name,
                            target_symbol=tgt_name,
                            file_path=fpath,
                            line_start=lstart,
                            line_end=lend,
                            evidence_ref=evidence_ref,
                            description=(
                                f"Architectural violation of '{rule.name}': {src_name} ({src_cls.get('stereotype', 'Unknown')}) "
                                f"forbiddenly references {tgt_name} ({tgt_cls.get('stereotype', 'Unknown')}) via {ref_kind}."
                            ),
                            metadata={"rule_id": rule.rule_id, "ref_kind": ref_kind},
                        ))

        return violations

    def _evaluate_required_annotation_rule(
        self,
        rule: ArchitecturalRule,
        classes: List[Dict[str, Any]],
        snapshot_identity: Tuple[str, str, Optional[str]],
    ) -> List[CandidateViolation]:
        repo_id, run_id, commit_hash = snapshot_identity
        violations: List[CandidateViolation] = []

        # Scope requirement check
        scope = rule.scope or {}
        if scope.get("require_explicit_config") and not rule.enabled:
            return []

        required_annos = scope.get("required_annotations") or [
            "preauthorize", "secured", "rolesallowed", "authenticated", "authorize"
        ]

        for cls in classes:
            if not matches_selector(cls, rule.source_selector):
                continue

            # Check if class-level or method-level has any of the required annotations
            class_annos = [str(a).lower().lstrip("@") for a in (cls.get("annotations") or [])]
            has_class_auth = any(any(req in a for req in required_annos) for a in class_annos)

            if has_class_auth:
                continue

            # Check methods
            for method in cls.get("methods", []):
                method_annos = [str(a).lower().lstrip("@") for a in (method.get("annotations") or [])]
                has_method_auth = any(any(req in a for req in required_annos) for a in method_annos)

                if not has_method_auth:
                    cname = cls.get("name", "")
                    mname = method.get("name", "unknown")
                    fpath = cls.get("file") or cls.get("file_path") or f"{cname}.java"
                    lstart = int(method.get("line_start") or cls.get("line_start") or 1)
                    lend = int(method.get("line_end") or lstart + 5)

                    evidence_ref = EvidenceRef(
                        repository_id=repo_id,
                        analysis_run_id=run_id,
                        commit_hash=commit_hash,
                        file_path=fpath,
                        line_start=lstart,
                        line_end=lend,
                        symbol_name=f"{cname}.{mname}",
                        evidence_type=EvidenceType.AST,
                    )

                    violations.append(CandidateViolation(
                        rule_id=rule.rule_id,
                        violation_type=rule.rule_type,
                        severity=rule.severity,
                        source_symbol=f"{cname}.{mname}",
                        target_symbol=None,
                        file_path=fpath,
                        line_start=lstart,
                        line_end=lend,
                        evidence_ref=evidence_ref,
                        description=(
                            f"Missing required security authorization annotation on endpoint '{cname}.{mname}'. "
                            f"Expected one of: {required_annos}"
                        ),
                        metadata={"rule_id": rule.rule_id, "method": mname},
                    ))

        return violations

    def verify_candidates(self, candidates: List[CandidateViolation]) -> List[GovernanceFinding]:
        """
        Passes candidate violations through EvidenceResolver.
        CRITICAL TRUTH BOUNDARY:
        Only assigns VERIFIED if EvidenceRef successfully resolves to valid snapshot source.
        Otherwise falls back to INSUFFICIENT_EVIDENCE or AI_SUGGESTION.
        """
        findings: List[GovernanceFinding] = []

        for cand in candidates:
            verdict = "INSUFFICIENT_EVIDENCE"
            resolved_evidence_dict: Optional[Dict[str, Any]] = None

            if cand.evidence_ref:
                resolved = self.evidence_resolver.resolve(cand.evidence_ref)
                if resolved.status == ResolutionStatus.RESOLVED:
                    verdict = "VERIFIED"
                    resolved_evidence_dict = resolved.to_dict()
                elif resolved.status in (ResolutionStatus.UNKNOWN_SNAPSHOT, ResolutionStatus.FILE_NOT_FOUND):
                    verdict = "INSUFFICIENT_EVIDENCE"
                else:
                    verdict = "AI_SUGGESTION"
            else:
                verdict = "INSUFFICIENT_EVIDENCE"

            # Formulate committable fix suggestion
            committable_fix = self._suggest_fix(cand)

            findings.append(GovernanceFinding(
                rule_id=cand.rule_id,
                violation_type=cand.violation_type,
                severity=cand.severity,
                verdict=verdict,
                source_symbol=cand.source_symbol,
                target_symbol=cand.target_symbol,
                file_path=cand.file_path,
                line_start=cand.line_start,
                line_end=cand.line_end,
                evidence_ref=resolved_evidence_dict,
                description=cand.description,
                committable_fix=committable_fix,
                requires_user_action=True,
            ))

        return findings

    @staticmethod
    def _suggest_fix(cand: CandidateViolation) -> str:
        if cand.rule_id == "ARCH-001":
            return (
                f"Refactor '{cand.source_symbol}' to inject an intermediate Service interface "
                f"rather than depending directly on Repository '{cand.target_symbol}'."
            )
        elif cand.rule_id == "ARCH-002":
            return (
                f"Remove presentation/web dependency '{cand.target_symbol}' from domain entity '{cand.source_symbol}'. "
                f"Domain models should remain agnostic of web infrastructure."
            )
        elif "IMPORT" in cand.rule_id or cand.violation_type == CycleType.IMPORT_CYCLE.value:
            return (
                f"Break circular import chain involving '{cand.source_symbol}'. Extract common dependencies "
                f"into a shared interface or utility module."
            )
        elif "INHERITANCE" in cand.rule_id or cand.violation_type == CycleType.INHERITANCE_CYCLE.value:
            return (
                f"Eliminate inheritance cycle involving '{cand.source_symbol}'. Favor composition over inheritance "
                f"or separate the class hierarchy."
            )
        elif "CALL" in cand.rule_id or cand.violation_type == CycleType.CALL_GRAPH_CYCLE.value:
            return (
                f"Decouple recursive cross-service invocations involving '{cand.source_symbol}'. "
                f"Introduce an event-driven message queue or an orchestrator."
            )
        elif cand.rule_id == "ARCH-004":
            return (
                f"Add @PreAuthorize(\"hasRole('USER')\") or equivalent method security annotation to '{cand.source_symbol}'."
            )
        return "Review and refactor architectural boundary violation."
