"""
Unit tests for Myers Line-Diff Engine and Committable Suggestions.
"""

from devlensx.review.suggestdiff import (
    compute_line_diff,
    format_suggestion_patch,
    attach_suggestion_diff_to_finding,
    DiffLineType,
)


def test_compute_line_diff_simple_edit():
    old = [
        "public void submit() {",
        "    doProcess();",
        "}",
    ]
    new = [
        "public void submit() {",
        "    if (isValid()) {",
        "        doProcess();",
        "    }",
        "}",
    ]
    diff = compute_line_diff(old, new)
    assert len(diff) > 0

    added = [dl.content for dl in diff if dl.type == DiffLineType.ADDED]
    deleted = [dl.content for dl in diff if dl.type == DiffLineType.DELETED]
    context = [dl.content for dl in diff if dl.type == DiffLineType.CONTEXT]

    assert "    if (isValid()) {" in added
    assert "public void submit() {" in context
    assert "}" in context
    # Re-indented doProcess() line is marked edited (deleted with 4 spaces, added with 8 spaces)
    assert "    doProcess();" in deleted
    assert "        doProcess();" in added


def test_format_suggestion_patch_explicit_action_invariants():
    old_code = "String token = req.getHeader(\"X-Token\");"
    new_code = "String token = sanitize(req.getHeader(\"X-Token\"));"

    patch = format_suggestion_patch(old_code, new_code, "auth/token.ts", start_line=42)
    assert patch["file"] == "auth/token.ts"
    assert patch["start_line"] == 42
    assert "-String token = req.getHeader(\"X-Token\");" in patch["unified_patch"]
    assert "+String token = sanitize(req.getHeader(\"X-Token\"));" in patch["unified_patch"]

    # Invariants
    assert patch["committable"] is True
    assert patch["verified"] is False
    assert patch["requires_user_action"] is True


def test_attach_suggestion_diff_to_finding():
    finding = {
        "file": "src/App.tsx",
        "line_start": 15,
        "line_end": 16,
        "existing_code": "<button onClick={handleClick}>Click</button>",
        "suggested_fix": "<button type=\"button\" onClick={handleClick}>Click</button>",
    }
    enriched = attach_suggestion_diff_to_finding(finding)
    assert "diff_snippet" in enriched
    assert enriched["diff_snippet"]["deleted"] == ["<button onClick={handleClick}>Click</button>"]
    assert enriched["diff_snippet"]["added"] == ["<button type=\"button\" onClick={handleClick}>Click</button>"]
    assert enriched["committable_suggestion"] == "<button type=\"button\" onClick={handleClick}>Click</button>"
    assert enriched["patch_metadata"]["requires_user_action"] is True
    assert enriched["patch_metadata"]["verified"] is False
