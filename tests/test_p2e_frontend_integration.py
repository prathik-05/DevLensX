"""
P2-E Targeted Test Suite: Frontend Integration & Build Verification
Validates:
1. Production bundle integrity (dist/index.html, CodeTurtle chunk, asset manifests).
2. CodeTurtle rebrand & backward-compatibility aliases across frontend surfaces.
3. Snapshot identity survival (frontend client contracts -> workspace API).
4. Strict claim taxonomy separation (AI_SUGGESTION vs VERIFIED EvidenceRefs).
5. Zero secrets in browser persistence / localStorage security invariant.
"""

import os
import re
import json
import pathlib
import pytest
from fastapi.testclient import TestClient

from devlensx.api.main import app
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.evidence.models import SnapshotRecord
from devlensx.core.persistence import get_storage_manager

client = TestClient(app)

WEB_DIR = pathlib.Path(r"C:\Users\SVCS\Desktop\DevLensX\web")
DIST_DIR = WEB_DIR / "dist"
SRC_DIR = WEB_DIR / "src"


def test_frontend_build_artifacts_exist():
    """Test 1: Verify production build output exists and is well-formed."""
    assert DIST_DIR.exists(), "web/dist directory does not exist. Run npm run build."
    index_html = DIST_DIR / "index.html"
    assert index_html.exists(), "dist/index.html missing"
    html_content = index_html.read_text(encoding="utf-8")
    assert "<div id=\"root\"></div>" in html_content
    assert "assets/" in html_content

    # Check that CodeTurtle bundle chunk exists
    assets = list((DIST_DIR / "assets").glob("*.js"))
    turtle_chunks = [a for a in assets if "CodeTurtleView" in a.name or "turtle" in a.name.lower()]
    assert len(turtle_chunks) >= 1, "CodeTurtleView bundle chunk missing from dist/assets"


def test_codeturtle_frontend_rebrand_and_aliases():
    """Test 2: Verify CodeTurtle is registered in page registry, App routes, and backward-compatible aliases exist."""
    registry_file = SRC_DIR / "pages" / "registry.ts"
    assert registry_file.exists()
    reg_content = registry_file.read_text(encoding="utf-8")

    assert "id: 'code-turtle'" in reg_content
    assert "label: 'Code Turtle'" in reg_content
    assert "path: '/code-turtle'" in reg_content
    assert "CodeTurtleView" in reg_content

    # App.tsx verification
    app_file = SRC_DIR / "App.tsx"
    assert app_file.exists()
    app_content = app_file.read_text(encoding="utf-8")
    assert "CodeTurtleView" in app_content
    assert "'code-turtle': CodeTurtleView" in app_content
    assert "'code-rabbit': CodeRabbitView" in app_content  # backward compatibility alias
    assert 'path="/code-turtle"' in app_content
    assert 'path="/code-rabbit"' in app_content  # backward compatibility route

    # Re-export compatibility file exists
    compat_file = SRC_DIR / "components" / "CodeRabbitView.tsx"
    assert compat_file.exists()
    compat_content = compat_file.read_text(encoding="utf-8")
    assert "CodeTurtleView" in compat_content
    assert "CodeRabbitView = CodeTurtleView" in compat_content


def test_snapshot_identity_survival_in_review_and_impact():
    """Test 3: Snapshot identity tuple (repo, run, commit) survives API path and fails closed for unknown runs."""
    unknown_run = "run_unknown_p2e_9999"

    # CodeTurtle review endpoint fails closed
    resp_rev = client.post(
        f"/api/workspace/{unknown_run}/review/codeturtle",
        json={"diff": "diff --git a/a.js b/a.js\n+1\n"}
    )
    assert resp_rev.status_code == 404

    # CodeRabbit alias endpoint fails closed
    resp_alias = client.post(
        f"/api/workspace/{unknown_run}/review/coderabbit",
        json={"diff": "diff --git a/a.js b/a.js\n+1\n"}
    )
    assert resp_alias.status_code == 404

    # Workspace change impact endpoint fails closed
    resp_imp = client.post(
        f"/api/workspace/{unknown_run}/impact",
        json={"target_symbol": "OrderController"}
    )
    assert resp_imp.status_code == 404

    # Workspace build plan endpoint fails closed
    resp_plan = client.post(
        f"/api/workspace/{unknown_run}/build/plan",
        json={"task": "Add logging", "target_symbol": "OrderController"}
    )
    assert resp_plan.status_code == 404


def test_claim_taxonomy_separation_no_promotion():
    """Test 4: Planner change steps strictly retain AI_SUGGESTION; evidence refs strictly retain VERIFIED."""
    repo_id = "test-taxonomy-repo"
    run_id = "run_p2e_taxonomy"
    commit = "deadbeef1234"

    model = {
        "repo": repo_id,
        "classes": [
            {"name": "TaxonomyTarget", "file": "src/Target.java", "line_start": 1, "line_end": 50, "injected_dependencies": []},
            {"name": "TaxonomyCaller", "file": "src/Caller.java", "line_start": 1, "line_end": 40, "injected_dependencies": ["TaxonomyTarget"]},
        ],
        "relationships": [{"source": "TaxonomyCaller", "target": "TaxonomyTarget", "type": "DEPENDS_ON"}],
    }
    snap = SnapshotRecord(repository_id=repo_id, analysis_run_id=run_id, repo_path="/tmp", commit_hash=commit)
    get_storage_manager().save_snapshot(snap, model)
    get_snapshot_registry().register(repo_id, run_id, "/tmp", commit)

    from devlensx.chat.orchestrator import _model_store
    _model_store[run_id] = model

    from devlensx.build.planner import BuildPlanner
    plan = BuildPlanner.plan("Refactor target", "TaxonomyTarget", run_id)

    # Invariant: Steps are proposals (AI_SUGGESTION), NEVER VERIFIED facts
    for step in plan.steps:
        assert step.status == "AI_SUGGESTION"
        assert step.source == "AI_SUGGESTION"
        assert step.status != "VERIFIED"

    # Invariant: EvidenceRefs are ground truth (VERIFIED)
    for ref in plan.evidence_refs:
        assert ref.get("status") == "VERIFIED"
        assert ref.get("repository_id") == repo_id
        assert ref.get("analysis_run_id") == run_id


def test_zero_secrets_in_localstorage():
    """Test 5: Audit all frontend code to ensure API keys and secrets are never stored in localStorage."""
    pattern = re.compile(r"localStorage\.setItem\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
    allowed_keys = {
        "devlensx_auth_token",
        "devlensx_llm_provider",
        "devlensx_graph_db",
        "devlensx_aux_open",
        "devlensx_theme",
    }

    found_keys = set()
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith((".ts", ".tsx", ".js", ".jsx")):
                path = os.path.join(root, file)
                content = open(path, "r", encoding="utf-8").read()
                matches = pattern.findall(content)
                for m in matches:
                    found_keys.add(m)

    disallowed = found_keys - allowed_keys
    assert not disallowed, f"SECURITY VIOLATION: Disallowed keys stored in localStorage: {disallowed}"
