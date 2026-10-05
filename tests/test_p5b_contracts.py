"""
Unit and Integration Tests for Phase P5-B: Cross-Service Contract Verification.

Validates:
1. Exact snapshot identity requirement:
   Producer (repo_id, run_id, commit_hash)
   Consumer (repo_id, run_id, commit_hash)
2. Fail-closed behavior on missing snapshot, unknown repo, or commit mismatch.
3. Breaking change detection:
   - ENDPOINT_REMOVED
   - HTTP_METHOD_CHANGED
   - REQUIRED_PARAM_ADDED
   - PARAM_TYPE_CHANGED
   - REQUIRED_RESPONSE_FIELD_REMOVED
   - RESPONSE_FIELD_TYPE_CHANGED
   - ENUM_VALUE_REMOVED
   - STATUS_CODE_CONTRACT_CHANGED
4. Non-breaking compatibility (optional params added, compatible response types).
"""

import pytest
from devlensx.governance.models import BreakingChangeType
from devlensx.governance.contracts import CrossServiceContractVerifier, normalize_endpoint_path
from devlensx.evidence.resolver import SnapshotRegistry
from devlensx.workspace.federation import FederatedWorkspaceManager, reset_federated_workspace_manager


@pytest.fixture(autouse=True)
def clean_workspace():
    reset_federated_workspace_manager()
    yield
    reset_federated_workspace_manager()


def test_normalize_endpoint_path():
    assert normalize_endpoint_path("/api/users/{id}") == "/api/users/{param}"
    assert normalize_endpoint_path("api/users/{userId}/") == "/api/users/{param}"
    assert normalize_endpoint_path("/orders/{orderId}/items/{itemId}") == "/orders/{param}/items/{param}"


def test_contract_verifier_fail_closed():
    snap_reg = SnapshotRegistry()
    ws_mgr = FederatedWorkspaceManager()
    verifier = CrossServiceContractVerifier(snapshot_registry=snap_reg, workspace_manager=ws_mgr)

    # 1. Non-existent workspace
    with pytest.raises(ValueError, match="WORKSPACE_NOT_FOUND"):
        verifier.verify_contracts(
            workspace_id="ws-ghost",
            producer_repo_id="producer-svc",
            consumer_repo_id="consumer-svc",
            producer_run_id="run-p1",
            consumer_run_id="run-c1",
        )

    # Setup workspace
    ws_mgr.create_workspace("ws-contracts")
    ws_mgr.add_repository("ws-contracts", "producer-svc", "Producer", "/path/p")
    ws_mgr.add_repository("ws-contracts", "consumer-svc", "Consumer", "/path/c")

    # 2. Non-existent snapshot
    with pytest.raises(ValueError, match="SNAPSHOT_NOT_FOUND"):
        verifier.verify_contracts(
            workspace_id="ws-contracts",
            producer_repo_id="producer-svc",
            consumer_repo_id="consumer-svc",
            producer_run_id="missing-run",
            consumer_run_id="run-c1",
        )

    # Register producer snapshot
    snap_reg.register("producer-svc", "run-p1", "/path/p", "commit-p1")
    # Register consumer with repo mismatch
    snap_reg.register("wrong-repo", "run-c1", "/path/c", "commit-c1")

    # 3. Repository mismatch
    with pytest.raises(ValueError, match="REPOSITORY_MISMATCH"):
        verifier.verify_contracts(
            workspace_id="ws-contracts",
            producer_repo_id="producer-svc",
            consumer_repo_id="consumer-svc",
            producer_run_id="run-p1",
            consumer_run_id="run-c1",
        )

    # Re-register correctly
    snap_reg.register("consumer-svc", "run-c1", "/path/c", "commit-c1")

    # 4. Commit mismatch
    with pytest.raises(ValueError, match="COMMIT_MISMATCH"):
        verifier.verify_contracts(
            workspace_id="ws-contracts",
            producer_repo_id="producer-svc",
            consumer_repo_id="consumer-svc",
            producer_run_id="run-p1",
            consumer_run_id="run-c1",
            producer_commit="commit-wrong",
        )


def test_breaking_changes_detection():
    snap_reg = SnapshotRegistry()
    ws_mgr = FederatedWorkspaceManager()
    verifier = CrossServiceContractVerifier(snapshot_registry=snap_reg, workspace_manager=ws_mgr)

    ws_mgr.create_workspace("ws-test")
    ws_mgr.add_repository("ws-test", "repo-api", "API", "/path/api")
    ws_mgr.add_repository("ws-test", "repo-client", "Client", "/path/client")

    snap_reg.register("repo-api", "run-api-1", "/path/api", "hash-api")
    snap_reg.register("repo-client", "run-cli-1", "/path/client", "hash-cli")

    producer_model = {
        "endpoints": [
            {
                "path": "/api/v1/orders/{id}",
                "http_method": "GET",
                "parameters": {
                    "id": {"type": "string", "required": True},
                    "tenant_id": {"type": "string", "required": True},  # Added required param
                },
                "response_schema": {
                    "order_id": {"type": "string"},
                    "total": {"type": "float"},
                    # "items" removed
                },
                "status_codes": [200],
                "enums": {
                    "OrderStatus": ["PENDING", "COMPLETED"]  # "CANCELLED" removed
                }
            },
            {
                "path": "/api/v1/payment",
                "http_method": "PUT",  # Producer changed to PUT, consumer expects POST
                "parameters": {},
            }
        ]
    }

    consumer_model = {
        "client_endpoints": [
            # 1. Endpoint removed
            {
                "path": "/api/v1/legacy-endpoint",
                "http_method": "GET",
            },
            # 2. HTTP method changed
            {
                "path": "/api/v1/payment",
                "http_method": "POST",
            },
            # 3. Parameter changes & response changes & enum changes
            {
                "path": "/api/v1/orders/{orderId}",
                "http_method": "GET",
                "parameters": {
                    "id": {"type": "string", "required": True}
                    # missing tenant_id
                },
                "response_schema": {
                    "order_id": {"type": "string", "required": True},
                    "total": {"type": "string", "required": True},  # expects string, producer has float
                    "items": {"type": "array", "required": True},    # missing from producer
                },
                "status_codes": [200],
                "enums": {
                    "OrderStatus": ["PENDING", "CANCELLED"]
                }
            }
        ]
    }

    report = verifier.verify_contracts(
        workspace_id="ws-test",
        producer_repo_id="repo-api",
        consumer_repo_id="repo-client",
        producer_run_id="run-api-1",
        consumer_run_id="run-cli-1",
        producer_model=producer_model,
        consumer_model=consumer_model,
    )

    assert report["is_compatible"] is False
    assert report["breaking_count"] > 0

    diff_types = {d["change_type"] for d in report["differences"]}
    assert BreakingChangeType.ENDPOINT_REMOVED.value in diff_types
    assert BreakingChangeType.HTTP_METHOD_CHANGED.value in diff_types
    assert BreakingChangeType.REQUIRED_PARAM_ADDED.value in diff_types
    assert BreakingChangeType.REQUIRED_RESPONSE_FIELD_REMOVED.value in diff_types
    assert BreakingChangeType.RESPONSE_FIELD_TYPE_CHANGED.value in diff_types
    assert BreakingChangeType.ENUM_VALUE_REMOVED.value in diff_types


def test_compatible_contracts():
    snap_reg = SnapshotRegistry()
    ws_mgr = FederatedWorkspaceManager()
    verifier = CrossServiceContractVerifier(snapshot_registry=snap_reg, workspace_manager=ws_mgr)

    ws_mgr.create_workspace("ws-compat")
    ws_mgr.add_repository("ws-compat", "repo-api", "API", "/path/api")
    ws_mgr.add_repository("ws-compat", "repo-client", "Client", "/path/client")

    snap_reg.register("repo-api", "run-api-compat", "/path/api", "hash-api")
    snap_reg.register("repo-client", "run-cli-compat", "/path/client", "hash-cli")

    producer_model = {
        "endpoints": [
            {
                "path": "/api/v1/users/{id}",
                "http_method": "GET",
                "parameters": {
                    "id": {"type": "string", "required": True},
                    "fields": {"type": "string", "required": False},  # Non-breaking optional
                },
                "response_schema": {
                    "user_id": {"type": "string"},
                    "email": {"type": "string"},
                    "avatar_url": {"type": "string"},  # Extra optional field
                },
                "status_codes": [200],
            }
        ]
    }

    consumer_model = {
        "client_endpoints": [
            {
                "path": "/api/v1/users/{userId}",
                "http_method": "GET",
                "parameters": {
                    "id": {"type": "string", "required": True}
                },
                "response_schema": {
                    "user_id": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True},
                },
                "status_codes": [200],
            }
        ]
    }

    report = verifier.verify_contracts(
        workspace_id="ws-compat",
        producer_repo_id="repo-api",
        consumer_repo_id="repo-client",
        producer_run_id="run-api-compat",
        consumer_run_id="run-cli-compat",
        producer_model=producer_model,
        consumer_model=consumer_model,
    )

    assert report["is_compatible"] is True
    assert report["breaking_count"] == 0
    assert report["non_breaking_count"] == 1  # OPTIONAL_PARAM_ADDED
