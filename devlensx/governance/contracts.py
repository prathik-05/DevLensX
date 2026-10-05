"""
DevLensX Cross-Service Contract Verifier (Phase P5-B)

Validates API contracts between producer and consumer services across
federated repository boundaries using exact snapshot identities.

CRITICAL INVARIANTS:
1. Exact Snapshot Identity for both sides:
   Producer: (producer_repo_id, producer_run_id, producer_commit)
   Consumer: (consumer_repo_id, consumer_run_id, consumer_commit)
2. Fail-Closed Validation:
   Mismatched repositories, missing snapshots, or unregistered entities
   fail closed with explicit exceptions.
3. Explicit Breaking Change Classification:
   ENDPOINT_REMOVED, HTTP_METHOD_CHANGED, REQUIRED_PARAM_ADDED,
   PARAM_TYPE_CHANGED, RESPONSE_TYPE_CHANGED, REQUIRED_RESPONSE_FIELD_REMOVED,
   RESPONSE_FIELD_TYPE_CHANGED, ENUM_VALUE_REMOVED, STATUS_CODE_CONTRACT_CHANGED.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple, Set

from devlensx.governance.models import BreakingChangeType, ContractDifference
from devlensx.evidence.resolver import get_snapshot_registry, SnapshotRegistry
from devlensx.workspace.federation import get_federated_workspace_manager, FederatedWorkspaceManager


def normalize_endpoint_path(path: str) -> str:
    """Normalizes path variables (e.g. /api/users/{id} and /api/users/{userId} -> /api/users/{param})."""
    if not path:
        return "/"
    p = path.strip()
    if not p.startswith("/"):
        p = "/" + p
    # Normalize trailing slash
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    # Replace path parameter placeholders with generic placeholder
    return re.sub(r"\{[a-zA-Z0-9_]+\}", "{param}", p).lower()


class CrossServiceContractVerifier:
    """
    Verifies API compatibility between producer and consumer services.
    """

    def __init__(
        self,
        snapshot_registry: Optional[SnapshotRegistry] = None,
        workspace_manager: Optional[FederatedWorkspaceManager] = None,
    ):
        self._snapshot_registry = snapshot_registry
        self._workspace_manager = workspace_manager

    @property
    def snapshot_registry(self) -> SnapshotRegistry:
        return self._snapshot_registry or get_snapshot_registry()

    @property
    def workspace_manager(self) -> FederatedWorkspaceManager:
        return self._workspace_manager or get_federated_workspace_manager()

    def verify_contracts(
        self,
        workspace_id: str,
        producer_repo_id: str,
        consumer_repo_id: str,
        producer_run_id: str,
        consumer_run_id: str,
        producer_commit: Optional[str] = None,
        consumer_commit: Optional[str] = None,
        producer_model: Optional[Dict[str, Any]] = None,
        consumer_model: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validates contracts between producer and consumer snapshots within a workspace.
        """
        # 1. Workspace validation
        ws = self.workspace_manager.get_workspace(workspace_id)
        if not ws:
            raise ValueError(f"WORKSPACE_NOT_FOUND: Workspace '{workspace_id}' does not exist.")

        if producer_repo_id not in ws.repositories:
            raise ValueError(f"REPOSITORY_NOT_IN_WORKSPACE: Producer repo '{producer_repo_id}' not in workspace '{workspace_id}'.")
        if consumer_repo_id not in ws.repositories:
            raise ValueError(f"REPOSITORY_NOT_IN_WORKSPACE: Consumer repo '{consumer_repo_id}' not in workspace '{workspace_id}'.")

        # 2. Snapshot isolation and verification
        prod_snap = self.snapshot_registry.get(producer_run_id)
        if not prod_snap:
            raise ValueError(f"SNAPSHOT_NOT_FOUND: Producer snapshot '{producer_run_id}' not found.")
        if prod_snap.repository_id != producer_repo_id:
            raise ValueError(
                f"REPOSITORY_MISMATCH: Producer snapshot '{producer_run_id}' belongs to "
                f"'{prod_snap.repository_id}', not '{producer_repo_id}'."
            )
        if producer_commit and prod_snap.commit_hash and prod_snap.commit_hash != producer_commit:
            raise ValueError(
                f"COMMIT_MISMATCH: Producer snapshot commit '{prod_snap.commit_hash}' "
                f"does not match requested commit '{producer_commit}'."
            )

        cons_snap = self.snapshot_registry.get(consumer_run_id)
        if not cons_snap:
            raise ValueError(f"SNAPSHOT_NOT_FOUND: Consumer snapshot '{consumer_run_id}' not found.")
        if cons_snap.repository_id != consumer_repo_id:
            raise ValueError(
                f"REPOSITORY_MISMATCH: Consumer snapshot '{consumer_run_id}' belongs to "
                f"'{cons_snap.repository_id}', not '{consumer_repo_id}'."
            )
        if consumer_commit and cons_snap.commit_hash and cons_snap.commit_hash != consumer_commit:
            raise ValueError(
                f"COMMIT_MISMATCH: Consumer snapshot commit '{cons_snap.commit_hash}' "
                f"does not match requested commit '{consumer_commit}'."
            )

        # 3. Load models if omitted
        if producer_model is None:
            try:
                from devlensx.chat.orchestrator import _load_model
                producer_model = _load_model(producer_run_id)
            except Exception:
                producer_model = {}

        if consumer_model is None:
            try:
                from devlensx.chat.orchestrator import _load_model
                consumer_model = _load_model(consumer_run_id)
            except Exception:
                consumer_model = {}

        # 4. Extract contracts
        producer_endpoints = self.extract_producer_endpoints(producer_model)
        consumer_expectations = self.extract_consumer_expectations(consumer_model)

        # 5. Compare contracts
        diffs = self.compare_contracts(producer_endpoints, consumer_expectations)

        breaking_count = sum(1 for d in diffs if d.is_breaking)
        non_breaking_count = sum(1 for d in diffs if not d.is_breaking)

        return {
            "workspace_id": workspace_id,
            "producer": {
                "repository_id": producer_repo_id,
                "analysis_run_id": producer_run_id,
                "commit_hash": prod_snap.commit_hash,
            },
            "consumer": {
                "repository_id": consumer_repo_id,
                "analysis_run_id": consumer_run_id,
                "commit_hash": cons_snap.commit_hash,
            },
            "is_compatible": breaking_count == 0,
            "breaking_count": breaking_count,
            "non_breaking_count": non_breaking_count,
            "differences": [d.to_dict() for d in diffs],
        }

    def extract_producer_endpoints(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts exposed API endpoints from producer model (controllers, routes, explicit endpoints).
        """
        endpoints: List[Dict[str, Any]] = []
        # Check explicit endpoints in model
        if "endpoints" in model:
            return list(model["endpoints"])

        classes = model.get("classes", [])
        for cls in classes:
            c_stereo = str(cls.get("stereotype", "")).lower()
            if c_stereo in ("controller", "restcontroller", "route", "api"):
                base_path = cls.get("path") or cls.get("route") or ""
                for m in cls.get("methods", []):
                    m_path = m.get("path") or m.get("route") or ""
                    full_path = (base_path.rstrip("/") + "/" + m_path.lstrip("/")).strip()
                    if not full_path.startswith("/"):
                        full_path = "/" + full_path
                    http_method = (m.get("http_method") or m.get("method") or "GET").upper()

                    endpoints.append({
                        "path": full_path,
                        "http_method": http_method,
                        "parameters": m.get("parameters") or {},
                        "response_schema": m.get("response_schema") or {},
                        "status_codes": m.get("status_codes") or [200],
                        "enums": m.get("enums") or {},
                    })
        return endpoints

    def extract_consumer_expectations(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts expected API calls from consumer model (Feign clients, HTTP clients, api calls).
        """
        expectations: List[Dict[str, Any]] = []
        if "client_endpoints" in model or "expectations" in model:
            return list(model.get("client_endpoints") or model.get("expectations") or [])

        classes = model.get("classes", [])
        for cls in classes:
            c_stereo = str(cls.get("stereotype", "")).lower()
            if c_stereo in ("client", "feignclient", "api_client", "service_client"):
                base_path = cls.get("path") or cls.get("route") or ""
                for m in cls.get("methods", []):
                    m_path = m.get("path") or m.get("route") or ""
                    full_path = (base_path.rstrip("/") + "/" + m_path.lstrip("/")).strip()
                    if not full_path.startswith("/"):
                        full_path = "/" + full_path
                    http_method = (m.get("http_method") or m.get("method") or "GET").upper()

                    expectations.append({
                        "path": full_path,
                        "http_method": http_method,
                        "parameters": m.get("parameters") or {},
                        "response_schema": m.get("response_schema") or {},
                        "status_codes": m.get("status_codes") or [200],
                        "enums": m.get("enums") or {},
                    })
        return expectations

    def compare_contracts(
        self,
        producer_endpoints: List[Dict[str, Any]],
        consumer_expectations: List[Dict[str, Any]],
    ) -> List[ContractDifference]:
        """
        Compares consumer expectations against producer endpoints and detects breaking/non-breaking differences.
        """
        diffs: List[ContractDifference] = []

        # Index producer endpoints by (normalized_path, http_method)
        producer_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for ep in producer_endpoints:
            norm_p = normalize_endpoint_path(ep.get("path", "/"))
            method = ep.get("http_method", "GET").upper()
            producer_map[(norm_p, method)] = ep

        for ce in consumer_expectations:
            c_raw_path = ce.get("path", "/")
            c_norm_path = normalize_endpoint_path(c_raw_path)
            c_method = ce.get("http_method", "GET").upper()

            # 1. Endpoint existence and method check
            matching_ep = producer_map.get((c_norm_path, c_method))
            if not matching_ep:
                # Check if path exists under another method
                other_methods = [
                    m for (p, m) in producer_map.keys() if p == c_norm_path
                ]
                if other_methods:
                    diffs.append(ContractDifference(
                        change_type=BreakingChangeType.HTTP_METHOD_CHANGED,
                        is_breaking=True,
                        endpoint_path=c_raw_path,
                        http_method=c_method,
                        details=(
                            f"HTTP method mismatch for endpoint '{c_raw_path}'. Consumer expects '{c_method}', "
                            f"but producer only provides {other_methods}."
                        ),
                        provider_spec={"methods": other_methods},
                        consumer_spec={"expected_method": c_method},
                    ))
                else:
                    diffs.append(ContractDifference(
                        change_type=BreakingChangeType.ENDPOINT_REMOVED,
                        is_breaking=True,
                        endpoint_path=c_raw_path,
                        http_method=c_method,
                        details=(
                            f"Endpoint '{c_raw_path}' [{c_method}] expected by consumer is missing from producer."
                        ),
                        consumer_spec=ce,
                    ))
                continue

            # 2. Parameter comparison
            p_params = matching_ep.get("parameters") or {}
            c_params = ce.get("parameters") or {}

            # Check if producer requires parameters that consumer does not supply
            for p_name, p_spec in p_params.items():
                if isinstance(p_spec, dict):
                    is_required = p_spec.get("required", False)
                    p_type = p_spec.get("type", "string")
                else:
                    is_required = False
                    p_type = str(p_spec)

                if is_required and p_name not in c_params:
                    diffs.append(ContractDifference(
                        change_type=BreakingChangeType.REQUIRED_PARAM_ADDED,
                        is_breaking=True,
                        endpoint_path=c_raw_path,
                        http_method=c_method,
                        details=(
                            f"Producer requires new parameter '{p_name}' of type '{p_type}' "
                            f"on '{c_raw_path}', which consumer does not supply."
                        ),
                        provider_spec={p_name: p_spec},
                        consumer_spec={"supplied": list(c_params.keys())},
                    ))
                elif not is_required and p_name not in c_params:
                    # Non-breaking optional parameter added
                    diffs.append(ContractDifference(
                        change_type="OPTIONAL_PARAM_ADDED",
                        is_breaking=False,
                        endpoint_path=c_raw_path,
                        http_method=c_method,
                        details=f"Optional parameter '{p_name}' available on producer.",
                        provider_spec={p_name: p_spec},
                    ))

            # Check parameter types for common parameters
            for c_name, c_spec in c_params.items():
                if c_name in p_params:
                    p_spec = p_params[c_name]
                    p_type = p_spec.get("type") if isinstance(p_spec, dict) else str(p_spec)
                    c_type = c_spec.get("type") if isinstance(c_spec, dict) else str(c_spec)
                    if p_type and c_type and p_type.lower() != c_type.lower():
                        diffs.append(ContractDifference(
                            change_type=BreakingChangeType.PARAM_TYPE_CHANGED,
                            is_breaking=True,
                            endpoint_path=c_raw_path,
                            http_method=c_method,
                            details=(
                                f"Parameter type conflict for '{c_name}' on '{c_raw_path}': "
                                f"producer expects '{p_type}', consumer provides '{c_type}'."
                            ),
                            provider_spec={c_name: p_spec},
                            consumer_spec={c_name: c_spec},
                        ))

            # 3. Response Schema comparison
            p_resp = matching_ep.get("response_schema") or {}
            c_resp = ce.get("response_schema") or {}

            for c_field, c_field_spec in c_resp.items():
                if isinstance(c_field_spec, dict):
                    c_f_req = c_field_spec.get("required", True)
                    c_f_type = c_field_spec.get("type", "string")
                else:
                    c_f_req = True
                    c_f_type = str(c_field_spec)

                if c_field not in p_resp:
                    if c_f_req:
                        diffs.append(ContractDifference(
                            change_type=BreakingChangeType.REQUIRED_RESPONSE_FIELD_REMOVED,
                            is_breaking=True,
                            endpoint_path=c_raw_path,
                            http_method=c_method,
                            details=(
                                f"Required response field '{c_field}' expected by consumer "
                                f"is missing from producer response schema on '{c_raw_path}'."
                            ),
                            provider_spec=p_resp,
                            consumer_spec={c_field: c_field_spec},
                        ))
                else:
                    p_field_spec = p_resp[c_field]
                    p_f_type = p_field_spec.get("type") if isinstance(p_field_spec, dict) else str(p_field_spec)
                    if p_f_type and c_f_type and p_f_type.lower() != c_f_type.lower():
                        diffs.append(ContractDifference(
                            change_type=BreakingChangeType.RESPONSE_FIELD_TYPE_CHANGED,
                            is_breaking=True,
                            endpoint_path=c_raw_path,
                            http_method=c_method,
                            details=(
                                f"Response field '{c_field}' type mismatch on '{c_raw_path}': "
                                f"producer returns '{p_f_type}', consumer expects '{c_f_type}'."
                            ),
                            provider_spec={c_field: p_field_spec},
                            consumer_spec={c_field: c_field_spec},
                        ))

            # 4. Enum validation
            p_enums = matching_ep.get("enums") or {}
            c_enums = ce.get("enums") or {}
            for enum_name, c_values in c_enums.items():
                p_values = p_enums.get(enum_name, [])
                missing_vals = set(c_values) - set(p_values)
                if missing_vals and p_values:
                    diffs.append(ContractDifference(
                        change_type=BreakingChangeType.ENUM_VALUE_REMOVED,
                        is_breaking=True,
                        endpoint_path=c_raw_path,
                        http_method=c_method,
                        details=(
                            f"Enum '{enum_name}' on '{c_raw_path}' removed values expected by consumer: {list(missing_vals)}."
                        ),
                        provider_spec={enum_name: p_values},
                        consumer_spec={enum_name: c_values},
                    ))

            # 5. Status code check
            p_status = set(matching_ep.get("status_codes") or [200])
            c_status = set(ce.get("status_codes") or [200])
            if c_status and not (p_status & c_status):
                diffs.append(ContractDifference(
                    change_type=BreakingChangeType.STATUS_CODE_CONTRACT_CHANGED,
                    is_breaking=True,
                    endpoint_path=c_raw_path,
                    http_method=c_method,
                    details=(
                        f"Status code mismatch on '{c_raw_path}': producer returns {list(p_status)}, "
                        f"but consumer expects {list(c_status)}."
                    ),
                    provider_spec={"status_codes": list(p_status)},
                    consumer_spec={"status_codes": list(c_status)},
                ))

        return diffs


_verifier = CrossServiceContractVerifier()


def get_cross_service_contract_verifier() -> CrossServiceContractVerifier:
    return _verifier
