"""P1-I real-repository validation: spring-petclinic (Java), sp-portfolio
(TypeScript), battleship-python (Python).

Each repo runs the REAL pipeline (analyze -> reason -> wiki -> review ->
verify -> resolve) with the deterministic offline reviewer. Asserts per repo:
findings, evidence resolvability, snapshot identity, language behavior,
no Spring leakage, no fake paths, no hallucinated symbols — plus the three
frozen P1-H invariants (no evidence -> no VERIFIED; no cross-run data;
no repository mutation).
"""
import hashlib
from pathlib import Path

import pytest

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import _model_store, store_model
from devlensx.deep_reasoning import build_deep_reasoning
from devlensx.wiki import generate_wiki_pages
from devlensx.codereview import CodeRabbitEngine, ReviewConfig

REPOS = {
    "java": "eval_repos/spring-petclinic",
    "typescript": "eval_repos/sp-portfolio",
    "python": "eval_repos/battleship-python",
}
BANNED_NON_JAVA = ["@Valid", "@Transactional", "JPA", "Spring", "Lombok",
                   "BindingResult", "ControllerAdvice", "@Cacheable"]


def _hash_tree(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and "__pycache__" not in str(p) and ".git/" not in str(p):
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


@pytest.fixture(scope="module", params=sorted(REPOS))
def analyzed(request):
    lang = request.param
    repo = REPOS[lang]
    run_id = f"run_p1i_{lang}"
    intel = RepositoryIntelligenceEngine().analyze(repo)
    model = intel.model
    register_snapshot(model.get("repo", repo), run_id, repo, f"p1i-{lang}")
    store_model(run_id, model)
    yield {"lang": lang, "repo": repo, "run_id": run_id, "model": model,
           "graph": intel.graph_store, "before": _hash_tree(repo)}
    _model_store.pop(run_id, None)


def _review(model, run_id):
    eng = CodeRabbitEngine(ReviewConfig(provider="offline"))
    ctx = {
        "repo": model.get("repo", ""), "language": model.get("repo_summary", {}).get("language", ""),
        "framework": model.get("repo_summary", {}).get("framework", ""),
        "classes": model.get("classes", []), "relationships": model.get("relationships", []),
        "endpoints": model.get("endpoints", []),
    }
    snap = {"repository_id": model.get("repo", ""), "analysis_run_id": run_id,
            "commit_hash": f"p1i-{model.get('repo_summary', {}).get('language', '')}"}
    result = eng._mock_review("", context=ctx, snapshot=snap)
    return result, snap


# --- reasoning + wiki per repo ---

def test_purpose_names_real_components(analyzed):
    ctx, narratives = build_deep_reasoning(analyzed["model"], analyzed["graph"], [])
    assert narratives["purpose"].strip()
    top = [c["name"] for c in ctx.key_components[:6]]
    assert any(n in narratives["purpose"] for n in top), (analyzed["lang"], top)


def test_no_spring_leakage_non_java(analyzed):
    if analyzed["lang"] == "java":
        pytest.skip("Java may legitimately mention Spring")
    ctx, narratives = build_deep_reasoning(analyzed["model"], analyzed["graph"], [])
    blob = " ".join(narratives.values()) + " ".join(ctx.architectural_patterns)
    leaks = [b for b in BANNED_NON_JAVA if b.lower() in blob.lower()]
    assert not leaks, (analyzed["lang"], leaks)


def test_wiki_builds_with_narratives(analyzed):
    pages = generate_wiki_pages(analyzed["model"], analyzed["graph"], [],
                                analyzed["run_id"], analyzed["model"].get("repo", ""), None)
    assert pages
    ov = next(p for p in pages if p.id == "overview")
    headings = [s["heading"] for s in ov.sections]
    assert "What This Project Does" in headings
    assert any(len(str(s.get("content", ""))) > 50 for s in ov.sections)


def test_wiki_citations_reference_real_files(analyzed):
    pages = generate_wiki_pages(analyzed["model"], analyzed["graph"], [],
                                analyzed["run_id"], analyzed["model"].get("repo", ""), None)
    repo_files = {p.relative_to(analyzed["repo"]).as_posix().replace("\\", "/")
                  for p in Path(analyzed["repo"]).rglob("*") if p.is_file()}
    checked = 0
    for page in pages:
        for cite in (page.citations or [])[:4]:
            f = str(cite.get("file", "")).replace("\\", "/")
            if not f:
                continue
            checked += 1
            assert f in repo_files or f.split("/")[-1] in {r.split("/")[-1] for r in repo_files}, \
                (analyzed["lang"], f)
    assert checked > 0


# --- review per repo ---

def test_review_findings_have_verdicts(analyzed):
    result, _ = _review(analyzed["model"], analyzed["run_id"])
    assert result.findings
    for f in result.findings:
        assert f["verdict"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE", "NOT_VERIFIED")


def test_no_hallucinated_symbols(analyzed):
    result, _ = _review(analyzed["model"], analyzed["run_id"])
    names = {c.get("name") for c in analyzed["model"].get("classes", [])}
    for f in result.findings:
        for ref in f.get("evidence_refs", []):
            assert ref.get("symbol_name") in names, (analyzed["lang"], ref)


def test_no_fake_paths(analyzed):
    result, _ = _review(analyzed["model"], analyzed["run_id"])
    for f in result.findings:
        assert "..." not in (f.get("file", "") or "")
        for ref in f.get("evidence_refs", []):
            assert ".." not in (ref.get("file_path", "") or "").split("/")
            assert "\x00" not in (ref.get("file_path", "") or "")


def test_verified_refs_resolve_to_source(analyzed):
    from fastapi.testclient import TestClient
    from devlensx.api.main import app
    result, snap = _review(analyzed["model"], analyzed["run_id"])
    verified = [f for f in result.findings if f["verdict"] == "VERIFIED" and f["evidence_refs"]]
    assert verified, "expected at least one VERIFIED finding with refs"
    ref = verified[0]["evidence_refs"][0]
    r = TestClient(app).post("/api/evidence/resolve", json={
        "repository_id": ref["repository_id"], "analysis_run_id": ref["analysis_run_id"],
        "file_path": ref["file_path"], "line_start": ref["line_start"],
        "line_end": ref["line_end"], "commit_hash": ref["commit_hash"],
        "symbol_name": ref["symbol_name"],
    })
    assert r.status_code == 200
    assert r.json()["resolved"] is True


# --- frozen P1-H invariants, on real data ---

def test_invariant_no_evidence_no_verified(analyzed):
    result, _ = _review(analyzed["model"], analyzed["run_id"])
    for f in result.findings:
        if f["verdict"] == "VERIFIED":
            assert f["evidence_refs"], (analyzed["lang"], f["title"])


def test_invariant_no_cross_run_data(analyzed):
    from fastapi.testclient import TestClient
    from devlensx.api.main import app
    other_run = analyzed["run_id"] + "_other"
    register_snapshot("other-repo", other_run, analyzed["repo"], "other1")
    try:
        r = TestClient(app).post("/codereview/review-repo", json={
            "analysis_run_id": other_run, "repository_id": analyzed["model"].get("repo", ""),
        })
        # other_run has no model and (if repo matches loosely) must fail closed,
        # never serve this run's findings
        assert r.status_code in (404, 409)
    finally:
        _model_store.pop(other_run, None)


def test_invariant_no_mutation(analyzed):
    assert _hash_tree(analyzed["repo"]) == analyzed["before"]
