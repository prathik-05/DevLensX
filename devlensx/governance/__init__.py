"""
DevLensX Architectural Governance & Contract Verification Package (Phase P5)
"""

from devlensx.governance.models import (
    ArchitecturalRule,
    CandidateViolation,
    GovernanceFinding,
    CycleType,
    BreakingChangeType,
    ContractDifference,
)
from devlensx.governance.rules import (
    matches_selector,
    get_default_governance_rules,
    GovernanceRuleRegistry,
    get_governance_rule_registry,
)
from devlensx.governance.cycles import (
    detect_import_cycles,
    detect_inheritance_cycles,
    detect_call_graph_cycles,
)
from devlensx.governance.evaluator import (
    GovernanceEvaluator,
)
from devlensx.governance.contracts import (
    CrossServiceContractVerifier,
    get_cross_service_contract_verifier,
)

__all__ = [
    "ArchitecturalRule",
    "CandidateViolation",
    "GovernanceFinding",
    "CycleType",
    "BreakingChangeType",
    "ContractDifference",
    "matches_selector",
    "get_default_governance_rules",
    "GovernanceRuleRegistry",
    "get_governance_rule_registry",
    "detect_import_cycles",
    "detect_inheritance_cycles",
    "detect_call_graph_cycles",
    "GovernanceEvaluator",
    "CrossServiceContractVerifier",
    "get_cross_service_contract_verifier",
]
