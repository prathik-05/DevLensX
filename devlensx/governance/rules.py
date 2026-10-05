"""
DevLensX Architectural Rules & Selector Matching Engine (Phase P5)

Provides structured selectors (stereotype, package, symbol, annotation, module)
and standard built-in architectural governance rules.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional

from devlensx.governance.models import ArchitecturalRule, CycleType


def matches_selector(symbol: Dict[str, Any], selector: Optional[Dict[str, Any]]) -> bool:
    """
    Evaluates whether an AST symbol or class matches a structured selector.
    Supports stereotype, package, name_regex, annotations, module.
    """
    if not selector:
        return True

    # 1. Stereotype selector (case-insensitive)
    if "stereotype" in selector:
        target_stereo = str(selector["stereotype"]).lower()
        actual_stereo = str(symbol.get("stereotype", "")).lower()
        if actual_stereo != target_stereo:
            return False

    # 2. Package / Namespace selector (prefix match or exact)
    if "package" in selector:
        pkg_pattern = selector["package"]
        actual_pkg = symbol.get("package") or symbol.get("namespace") or ""
        # Also check file_path if package not explicitly in symbol
        file_path = symbol.get("file_path") or symbol.get("file") or ""
        if not (actual_pkg.startswith(pkg_pattern) or pkg_pattern.replace(".", "/") in file_path):
            return False

    # 3. Symbol Name selector
    if "name" in selector:
        if symbol.get("name") != selector["name"]:
            return False
    if "name_regex" in selector:
        if not re.search(selector["name_regex"], symbol.get("name", "")):
            return False

    # 4. Annotation selector (checks if class or any method has the annotation)
    if "annotation" in selector:
        req_anno = str(selector["annotation"]).lower().lstrip("@")
        annos = [str(a).lower().lstrip("@") for a in (symbol.get("annotations") or [])]
        for m in symbol.get("methods", []):
            annos.extend(str(a).lower().lstrip("@") for a in (m.get("annotations") or []))
        if not any(req_anno in a for a in annos):
            return False

    # 5. File / Module path pattern
    if "path_prefix" in selector:
        file_path = symbol.get("file_path") or symbol.get("file") or ""
        if not file_path.startswith(selector["path_prefix"]):
            return False

    return True


def get_default_governance_rules() -> List[ArchitecturalRule]:
    """Canonical built-in architectural governance rules."""
    return [
        ArchitecturalRule(
            rule_id="ARCH-001",
            name="Controller-Repository Boundary Bypass",
            rule_type="LAYER_HIERARCHY",
            scope={"languages": ["java", "python", "typescript", "csharp"]},
            source_selector={"stereotype": "Controller"},
            target_selector={"stereotype": "Repository"},
            constraint="FORBIDDEN",
            severity="CRITICAL",
            description="Controllers must access persistence strictly through a Service layer and never depend on Repositories directly.",
        ),
        ArchitecturalRule(
            rule_id="ARCH-002",
            name="Domain-Web Inversion Violation",
            rule_type="FORBIDDEN_DEPENDENCY",
            scope={"languages": ["java", "python", "typescript", "csharp", "go"]},
            source_selector={"stereotype": "Entity"},
            target_selector={"stereotype": "Controller"},
            constraint="FORBIDDEN",
            severity="CRITICAL",
            description="Domain entities and business models must not depend on Web / Controller infrastructure.",
        ),
        ArchitecturalRule(
            rule_id="ARCH-003-IMPORT",
            name="Package / Module Import Cycle",
            rule_type="CYCLE_DETECTION",
            scope={"cycle_type": CycleType.IMPORT_CYCLE.value},
            source_selector={},
            target_selector=None,
            constraint="NO_CYCLE",
            severity="WARNING",
            description="Modules or packages must not form circular import chains.",
        ),
        ArchitecturalRule(
            rule_id="ARCH-003-INHERITANCE",
            name="Class Inheritance Cycle",
            rule_type="CYCLE_DETECTION",
            scope={"cycle_type": CycleType.INHERITANCE_CYCLE.value},
            source_selector={},
            target_selector=None,
            constraint="NO_CYCLE",
            severity="CRITICAL",
            description="Classes or interfaces must not form circular inheritance or implementation loops.",
        ),
        ArchitecturalRule(
            rule_id="ARCH-003-CALL",
            name="Cross-Component Call Graph Recursion",
            rule_type="CYCLE_DETECTION",
            scope={"cycle_type": CycleType.CALL_GRAPH_CYCLE.value},
            source_selector={},
            target_selector=None,
            constraint="NO_CYCLE",
            severity="WARNING",
            description="Distinct service components must not form circular recursive call sequences.",
        ),
        ArchitecturalRule(
            rule_id="ARCH-004",
            name="Secured Endpoint Annotation Requirement",
            rule_type="REQUIRED_ANNOTATION",
            scope={"framework": "spring", "require_explicit_config": True},
            source_selector={"stereotype": "Controller", "require_auth": True},
            target_selector=None,
            constraint="REQUIRED",
            severity="WARNING",
            description="Secured controller endpoints must carry configured authorization annotations (@PreAuthorize, @Secured, or @RolesAllowed).",
        ),
    ]


class GovernanceRuleRegistry:
    """In-memory thread-safe registry of governance rules per workspace/session."""

    def __init__(self):
        self._rules: Dict[str, ArchitecturalRule] = {r.rule_id: r for r in get_default_governance_rules()}

    def get_rules(self, enabled_only: bool = True) -> List[ArchitecturalRule]:
        if enabled_only:
            return [r for r in self._rules.values() if r.enabled]
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[ArchitecturalRule]:
        return self._rules.get(rule_id)

    def register_rule(self, rule: ArchitecturalRule):
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def reset_defaults(self):
        self._rules = {r.rule_id: r for r in get_default_governance_rules()}


_default_registry = GovernanceRuleRegistry()


def get_governance_rule_registry() -> GovernanceRuleRegistry:
    return _default_registry
