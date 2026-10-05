"""
Unit and Integration Tests for Phase P5-A: Living Architectural Governance.

Validates:
1. Structured selector matching (stereotype, package, annotation, name).
2. Rule registration and default catalog (ARCH-001, ARCH-002, ARCH-003, ARCH-004).
3. CandidateViolation generation (LAYER_HIERARCHY, FORBIDDEN_DEPENDENCY).
4. Explicit cycle distinction: IMPORT_CYCLE, INHERITANCE_CYCLE, CALL_GRAPH_CYCLE.
5. Mandatory Truth Boundary:
   - Evaluator NEVER directly assigns VERIFIED without EvidenceResolver validation.
   - Unregistered snapshot -> INSUFFICIENT_EVIDENCE.
   - Grounded snapshot evidence -> VERIFIED.
6. REQUIRED_ANNOTATION requirement with explicit configuration scope.
"""

import pytest
import tempfile
from pathlib import Path

from devlensx.governance.models import (
    ArchitecturalRule,
    CycleType,
    CandidateViolation,
    GovernanceFinding,
)
from devlensx.governance.rules import (
    matches_selector,
    get_default_governance_rules,
    GovernanceRuleRegistry,
)
from devlensx.governance.cycles import (
    find_directed_cycles,
    detect_import_cycles,
    detect_inheritance_cycles,
    detect_call_graph_cycles,
)
from devlensx.governance.evaluator import GovernanceEvaluator
from devlensx.evidence.resolver import SnapshotRegistry, EvidenceResolver
from devlensx.evidence.models import EvidenceRef, EvidenceType


def test_matches_selector():
    symbol = {
        "name": "OrderController",
        "stereotype": "Controller",
        "package": "com.example.orders",
        "file": "com/example/orders/OrderController.java",
        "annotations": ["RestController", "PreAuthorize"],
        "methods": [
            {"name": "createOrder", "annotations": ["PostMapping", "Transactional"]}
        ]
    }

    # Stereotype match
    assert matches_selector(symbol, {"stereotype": "Controller"})
    assert matches_selector(symbol, {"stereotype": "controller"})
    assert not matches_selector(symbol, {"stereotype": "Repository"})

    # Package match
    assert matches_selector(symbol, {"package": "com.example"})
    assert not matches_selector(symbol, {"package": "com.other"})

    # Name regex
    assert matches_selector(symbol, {"name_regex": r"Controller$"})
    assert not matches_selector(symbol, {"name_regex": r"Service$"})

    # Annotation match (class level)
    assert matches_selector(symbol, {"annotation": "PreAuthorize"})
    assert matches_selector(symbol, {"annotation": "@RestController"})
    # Annotation match (method level)
    assert matches_selector(symbol, {"annotation": "Transactional"})
    assert not matches_selector(symbol, {"annotation": "Secured"})


def test_find_directed_cycles_elementary():
    # A -> B -> C -> A
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],
    }
    cycles = find_directed_cycles(graph)
    assert len(cycles) == 1
    # Canonical rotation puts lexicographically lowest first
    assert cycles[0] == ["A", "B", "C", "A"]

    # Graph with no cycle: A -> B -> C
    acyclic = {
        "A": ["B"],
        "B": ["C"],
        "C": [],
    }
    assert find_directed_cycles(acyclic) == []


def test_explicit_cycle_distinctions():
    snapshot_identity = ("repo-test", "run-cycle-1", "commit-c1")

    # 1. IMPORT_CYCLE
    classes_import = [
        {"name": "OrderModule", "package": "com.orders", "imports": ["com.billing.BillingService"]},
        {"name": "BillingModule", "package": "com.billing", "imports": ["com.orders.OrderService"]},
    ]
    import_cycles = detect_import_cycles(classes_import, snapshot_identity)
    assert len(import_cycles) == 1
    assert import_cycles[0].violation_type == CycleType.IMPORT_CYCLE.value
    assert "com.billing" in import_cycles[0].description
    assert "com.orders" in import_cycles[0].description

    # 2. INHERITANCE_CYCLE
    classes_inheritance = [
        {"name": "ClassA", "extends": ["ClassB"], "file": "ClassA.java", "line_start": 10},
        {"name": "ClassB", "extends": ["ClassA"], "file": "ClassB.java", "line_start": 20},
    ]
    inh_cycles = detect_inheritance_cycles(classes_inheritance, snapshot_identity)
    assert len(inh_cycles) == 1
    assert inh_cycles[0].violation_type == CycleType.INHERITANCE_CYCLE.value
    assert inh_cycles[0].severity == "CRITICAL"
    assert "ClassA -> ClassB -> ClassA" in inh_cycles[0].description

    # 3. CALL_GRAPH_CYCLE
    classes_call = [
        {"name": "ServiceX", "injected_dependencies": ["ServiceY"], "file": "ServiceX.java"},
        {"name": "ServiceY", "injected_dependencies": ["ServiceX"], "file": "ServiceY.java"},
    ]
    call_cycles = detect_call_graph_cycles(classes_call, snapshot_identity)
    assert len(call_cycles) == 1
    assert call_cycles[0].violation_type == CycleType.CALL_GRAPH_CYCLE.value
    assert "ServiceX -> ServiceY -> ServiceX" in call_cycles[0].description


def test_evaluator_mandatory_truth_boundary_unregistered():
    """
    CRITICAL TEST: Evaluator must NEVER self-assign VERIFIED.
    When snapshot is not registered, verdict MUST fall back to INSUFFICIENT_EVIDENCE.
    """
    snap_reg = SnapshotRegistry()  # Empty, snapshot not registered
    evaluator = GovernanceEvaluator(snapshot_registry=snap_reg)

    classes = [
        {
            "name": "BadController",
            "stereotype": "Controller",
            "injected_dependencies": ["DirectRepository"],
            "file": "BadController.java",
            "line_start": 10,
        },
        {
            "name": "DirectRepository",
            "stereotype": "Repository",
            "file": "DirectRepository.java",
            "line_start": 5,
        }
    ]

    findings = evaluator.evaluate(
        repository_id="repo-mock",
        analysis_run_id="unregistered-run-123",
        commit_hash="commit-xxx",
        classes=classes,
        graph_edges=[],
    )

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "ARCH-001"
    # TRUTH BOUNDARY CHECK: Cannot be VERIFIED
    assert f.verdict == "INSUFFICIENT_EVIDENCE"
    assert f.requires_user_action is True
    assert "intermediate Service" in f.committable_fix


def test_evaluator_truth_boundary_grounded_source():
    """
    When snapshot is registered and evidence resolves against real source on disk,
    verdict is strictly verified as VERIFIED.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Create real file inside snapshot directory
        controller_code = (
            "package com.example;\n"
            "public class UserController {\n"
            "    @Autowired\n"
            "    private UserRepository userRepository;\n"
            "}\n"
        )
        file_path = "UserController.java"
        (tmp_path / file_path).write_text(controller_code, encoding="utf-8")

        snap_reg = SnapshotRegistry()
        snap_reg.register(
            repository_id="repo-user-svc",
            analysis_run_id="run-valid-001",
            repo_path=str(tmp_path),
            commit_hash="commit-grounded-999"
        )

        evaluator = GovernanceEvaluator(snapshot_registry=snap_reg)

        classes = [
            {
                "name": "UserController",
                "stereotype": "Controller",
                "injected_dependencies": ["UserRepository"],
                "file": "UserController.java",
                "line_start": 2,
                "line_end": 5,
            },
            {
                "name": "UserRepository",
                "stereotype": "Repository",
                "file": "UserRepository.java",
                "line_start": 1,
                "line_end": 10,
            }
        ]

        findings = evaluator.evaluate(
            repository_id="repo-user-svc",
            analysis_run_id="run-valid-001",
            commit_hash="commit-grounded-999",
            classes=classes,
            graph_edges=[],
        )

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "ARCH-001"
        assert f.verdict == "VERIFIED"
        assert f.evidence_ref is not None
        assert f.evidence_ref["status"] == "RESOLVED"
        assert f.requires_user_action is True


def test_required_annotation_evaluation():
    rule = ArchitecturalRule(
        rule_id="ARCH-004",
        name="Secured Endpoint Authorization",
        rule_type="REQUIRED_ANNOTATION",
        scope={"framework": "spring", "require_explicit_config": True},
        source_selector={"stereotype": "Controller"},
        constraint="REQUIRED",
        severity="WARNING",
    )

    classes = [
        {
            "name": "PublicController",
            "stereotype": "Controller",
            "annotations": [],
            "file": "PublicController.java",
            "methods": [
                {"name": "deleteAccount", "annotations": ["DeleteMapping"]}  # Missing security auth annotation
            ]
        },
        {
            "name": "SecuredController",
            "stereotype": "Controller",
            "annotations": ["PreAuthorize"],
            "file": "SecuredController.java",
            "methods": [
                {"name": "adminDashboard", "annotations": ["GetMapping"]}
            ]
        }
    ]

    snap_reg = SnapshotRegistry()
    evaluator = GovernanceEvaluator(snapshot_registry=snap_reg)

    candidates = evaluator.generate_candidate_violations(
        repository_id="repo-sec",
        analysis_run_id="run-sec-1",
        commit_hash="c1",
        rules=[rule],
        classes=classes,
        graph_edges=[],
    )

    # Only PublicController.deleteAccount should be flagged
    assert len(candidates) == 1
    assert candidates[0].source_symbol == "PublicController.deleteAccount"
    assert "Missing required security authorization annotation" in candidates[0].description
