"""P1-H review workspace UI tests (structural, repo convention).

Locks the UI invariants: candidates are progress-only, severity and verdict
render as independent dimensions, VERIFIED without evidence can never render
as verified, fixes are proposals with no apply path, diagrams render
server-produced topology, snapshot switches reset state.
"""
import pathlib

VIEW = (pathlib.Path("web/src/components/CodeTurtleView.tsx") if pathlib.Path("web/src/components/CodeTurtleView.tsx").exists() else pathlib.Path("web/src/components/CodeRabbitView.tsx")).read_text(encoding="utf-8")
API = pathlib.Path("web/src/apiClient.ts").read_text(encoding="utf-8")


def test_candidate_progress_never_rendered_as_finding():
    # candidate_found carries {index, candidate_id} and renders as progress chips
    assert "candidate_id" in VIEW
    assert "Candidates are progress only" in VIEW
    # progress section renders candidate ids, never title/severity/description
    assert "REVIEW PROGRESS" in VIEW
    assert "analyzing candidate" in VIEW.lower() or "analyzing" in VIEW


def test_severity_verdict_independent_badges():
    assert "RiskBadge" in VIEW and "VerificationBadge" in VIEW
    # both badges on the same card, neither derived from the other
    assert "toRiskLevel(f.severity)" in VIEW
    assert "displayVerdict(f)" in VIEW


def test_verified_without_evidence_never_renders_verified():
    assert "displayVerdict" in VIEW
    assert "treated as unverified" in VIEW or "NOT_VERIFIED" in VIEW
    # guard implementation present
    assert "evidence_refs" in VIEW and "length" in VIEW


def test_evidence_navigation_uses_sourceviewer():
    assert "SourceViewer" in VIEW
    assert "resolveEvidence" in VIEW or "loadEvidence" in VIEW
    # unresolved evidence states render (SourceViewer handles failure modes)
    assert "openEvidence" in VIEW


def test_no_apply_fix_path():
    assert "Apply Fix" not in VIEW and "applyFix" not in VIEW
    assert "PROPOSED FIX" in VIEW
    assert "never modifies" in VIEW or "never writes" in VIEW or "never modifies repository" in VIEW
    # ChangePlan is proposals-only display
    assert "createBuildPlan" in VIEW or "Open ChangePlan" in VIEW
    assert "AI_SUGGESTION" in VIEW


def test_diagram_renders_server_topology():
    assert "MermaidBlock" in VIEW
    assert "change_diagram" in VIEW or "diagram" in VIEW
    assert "GRAPH-DERIVED" in VIEW


def test_filters_for_severity_category_verdict():
    assert "sevFilter" in VIEW and "catFilter" in VIEW and "verFilter" in VIEW
    assert "Filter by severity" in VIEW
    assert "Filter by category" in VIEW
    assert "Filter by verification" in VIEW
    assert "INSUFFICIENT_EVIDENCE" in VIEW


def test_snapshot_identity_and_isolation():
    assert "repositoryId" in VIEW and "commitHash" in VIEW
    assert "runKey" in VIEW
    # switching runs resets review state
    assert "switching analysis runs resets" in VIEW


def test_stream_reader_and_error_states():
    assert "reviewStreamReview" in API
    assert "text/event-stream" not in API  # server sets content-type; client parses frames
    assert "onEvent(event, data)" in API or "onEvent(event, data: any)" in API
    assert "Stop" in VIEW and "AbortController" in VIEW
    assert "interrupted" in VIEW
    assert "MOCK" in VIEW or "FALLBACK" in VIEW
    assert "TRUNCATED" in VIEW


def test_suggestion_copy_and_markdown_copy():
    assert "Copy Suggestion" in VIEW
    assert "Copy as Markdown" in VIEW
    assert "copied" in VIEW


def test_landing_ctas_navigate():
    landing = pathlib.Path("web/src/components/LandingPage.tsx").read_text(encoding="utf-8")
    assert "useNavigate" in landing
    assert "navigate('/overview')" in landing
    assert "navigate('/wiki')" in landing
