"""P1-B matrix B (diff parsing) + C (AST/URM symbol resolution) tests."""
from devlensx.review.hunks import HunkParser
from devlensx.review.symbol_resolver import resolve_changed_symbols, summarize
from devlensx.review.diff_analyzer import DiffAnalyzer

MODEL = {
    "classes": [
        {"name": "OwnerController", "stereotype": "Controller", "kind": "class",
         "file": "src/owner/OwnerController.java", "line_start": 1, "line_end": 120,
         "annotations": ["Controller"], "metadata": {}},
        {"name": "create", "stereotype": "Method", "kind": "method",
         "file": "src/owner/OwnerController.java", "line_start": 40, "line_end": 70,
         "annotations": [], "is_test": False,
         "metadata": {"parent_class": "java_OwnerController_1"}},
        {"name": "Owner", "stereotype": "Entity", "kind": "class",
         "file": "src/owner/Owner.java", "line_start": 1, "line_end": 80,
         "annotations": ["Entity"], "metadata": {}},
    ]
}

DIFF_SINGLE = """diff --git a/src/owner/OwnerController.java b/src/owner/OwnerController.java
index 111..222 100644
--- a/src/owner/OwnerController.java
+++ b/src/owner/OwnerController.java
@@ -38,7 +38,9 @@ public class OwnerController {
     // unchanged context
     // unchanged context
-    String oldCall();
+    String newCall();
+    String addedCall();
     // unchanged context
     // unchanged context
     // unchanged context
"""

DIFF_MULTI = DIFF_SINGLE + """diff --git a/src/owner/Owner.java b/src/owner/Owner.java
index 333..444 100644
--- a/src/owner/Owner.java
+++ b/src/owner/Owner.java
@@ -10,3 +10,4 @@ public class Owner {
     private String a;
+    private String b;
     private String c;
"""


# --- B: single hunk ---

def test_single_hunk_ranges():
    res = HunkParser.parse(DIFF_SINGLE)
    assert len(res.files) == 1
    fd = res.files[0]
    assert fd.path == "src/owner/OwnerController.java"
    assert fd.status == "MODIFIED"
    assert len(fd.hunks) == 1
    h = fd.hunks[0]
    assert (h.old_start, h.new_start) == (38, 38)
    assert h.added == [40, 41] and h.removed == [40]
    assert res.truncated is False


def test_multi_hunk_and_multi_file():
    res = HunkParser.parse(DIFF_MULTI + "@@ -60,3 +61,4 @@\n x\n+y\n z\n")
    assert len(res.files) == 2
    assert sum(len(f.hunks) for f in res.files) == 3
    paths = [f.path for f in res.files]
    assert paths == ["src/owner/OwnerController.java", "src/owner/Owner.java"]


def test_new_deleted_rename_binary():
    new_file = ("diff --git a/new.py b/new.py\nnew file mode 100644\nindex 000..123\n"
                "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1,2 @@\n+line1\n+line2\n")
    gone = ("diff --git a/old.py b/old.py\ndeleted file mode 100644\nindex 123..000\n"
            "--- a/old.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-line1\n-line2\n")
    ren = ("diff --git a/a.py b/b.py\nsimilarity index 90%\nrename from a.py\nrename to b.py\n"
           "index 111..222\n--- a/a.py\n+++ b/b.py\n@@ -1,2 +1,2 @@\n x\n-y\n+z\n")
    binary = "diff --git a/img.png b/img.png\nindex 111..222 100644\nBinary files a/img.png and b/img.png differ\n"
    assert HunkParser.parse(new_file).files[0].status == "ADDED"
    assert HunkParser.parse(gone).files[0].status == "DELETED"
    rf = HunkParser.parse(ren).files[0]
    assert rf.status == "RENAMED" and rf.old_path == "a.py" and rf.path == "b.py"
    bf = HunkParser.parse(binary).files[0]
    assert bf.status == "BINARY" and bf.binary is True


def test_malformed_and_empty():
    assert HunkParser.parse("").files == []
    assert HunkParser.parse("just some text\nno headers\n").files == []
    # Hunk header without file block must not crash
    assert HunkParser.parse("@@ -1,2 +1,2 @@\n x\n").files == []


def test_malicious_paths_inert():
    evil = ("diff --git a/../../etc/passwd b/../../etc/passwd\nindex 111..222\n"
            "--- a/../../etc/passwd\n+++ b/../../etc/passwd\n@@ -1 +1 @@\n-x\n+y\n")
    res = HunkParser.parse(evil)
    assert len(res.files) == 1
    assert res.files[0].suspicious_path is True
    assert res.files[0].hunks[0].added == [1]
    nul = "diff --git a/a\x00b.py b/a\x00b.py\nindex 111..222\n--- a/a.py\n+++ b/b.py\n@@ -1 +1 @@\n-x\n+y\n"
    res2 = HunkParser.parse(nul)
    assert "\x00" not in res2.files[0].path


def test_truncation_bounds():
    many = "".join(
        f"diff --git a/f{i}.py b/f{i}.py\nindex 111..222\n--- a/f{i}.py\n+++ b/f{i}.py\n@@ -1 +1 @@\n-x\n+y\n"
        for i in range(60)
    )
    res = HunkParser.parse(many)
    assert res.truncated is True
    assert len(res.files) == 50


def test_summarize_bounded():
    s = summarize(HunkParser.parse(DIFF_MULTI))
    assert s["files"] == 2 and s["hunks"] == 2
    assert s["added_lines"] == 3 and s["removed_lines"] == 1


# --- C: AST/URM resolution ---

def test_method_innermost_scope():
    syms = resolve_changed_symbols(HunkParser.parse(DIFF_SINGLE), MODEL)
    names = {s.name for s in syms}
    # changed lines 40-41 fall inside create() [40,70]: method wins, class dropped
    assert "create" in names
    assert "OwnerController" not in names
    m = next(s for s in syms if s.name == "create")
    assert m.changed_lines == [40, 41] and m.removed_lines == [40]
    assert m.enclosing == "OwnerController" and m.evidence_kind == "changed-line"


def test_comment_string_false_positive():
    # Owner is only MENTIONED in a comment/string — no lines inside Owner.java range
    evil = ("diff --git a/src/owner/OwnerController.java b/src/owner/OwnerController.java\n"
            "index 111..222\n--- a/src/owner/OwnerController.java\n+++ b/src/owner/OwnerController.java\n"
            "@@ -100,3 +100,4 @@\n"
            ' // TODO: picks Owner entity here "\n'
            '+// Owner is great\n'
            ' x = "Owner";\n')
    syms = resolve_changed_symbols(HunkParser.parse(evil), MODEL)
    assert {s.name for s in syms} == set() or all(s.name != "Owner" for s in syms)


def test_new_deleted_file_resolution():
    new_file = ("diff --git a/src/owner/New.java b/src/owner/New.java\nnew file mode 100644\n"
                "--- /dev/null\n+++ b/src/owner/New.java\n@@ -0,0 +1,2 @@\n+a\n+b\n")
    model = {"classes": [{"name": "New", "stereotype": "Class", "kind": "class",
                          "file": "src/owner/New.java", "line_start": 1, "line_end": 2,
                          "annotations": [], "metadata": {}}]}
    syms = resolve_changed_symbols(HunkParser.parse(new_file), model)
    assert len(syms) == 1 and syms[0].change == "ADDED_FILE"
    assert syms[0].evidence_kind == "declaration"


def test_out_of_range_excluded():
    syms = resolve_changed_symbols(HunkParser.parse(DIFF_SINGLE), MODEL)
    assert all(s.name != "Owner" for s in syms)


def test_changed_symbols_backward_compat():
    out = DiffAnalyzer.changed_symbols(DIFF_SINGLE, MODEL)
    assert any(c["name"] == "create" for c in out)
    create = next(c for c in out if c["name"] == "create")
    assert create["diff_change"]["changed_lines"] == [40, 41]
    assert DiffAnalyzer.changed_files(DIFF_SINGLE) == ["src/owner/OwnerController.java"]


def test_rangeless_symbol_file_level_declaration_only():
    # Legacy/sparse models without line ranges still resolve by file,
    # but explicitly as declaration evidence — never changed-line evidence.
    model = {"classes": [{"name": "Legacy", "stereotype": "Class", "kind": "class",
                          "file": "src/Legacy.java", "annotations": [], "metadata": {}}]}
    diff = ("diff --git a/src/Legacy.java b/src/Legacy.java\n--- a/src/Legacy.java\n+++ b/src/Legacy.java\n"
            "@@ -1,2 +1,3 @@\n x\n-y\n+z\n+w\n")
    syms = resolve_changed_symbols(HunkParser.parse(diff), model)
    assert len(syms) == 1 and syms[0].name == "Legacy"
    assert syms[0].evidence_kind == "declaration"
    assert syms[0].changed_lines == [] and syms[0].removed_lines == []


def test_binary_file_yields_no_symbols():
    binary = ("diff --git a/img.png b/img.png\nindex 111..222\n"
              "Binary files a/img.png and b/img.png differ\n")
    model = {"classes": [{"name": "img", "stereotype": "Class", "kind": "class",
                          "file": "img.png", "line_start": 1, "line_end": 1,
                          "annotations": [], "metadata": {}}]}
    assert resolve_changed_symbols(HunkParser.parse(binary), model) == []
