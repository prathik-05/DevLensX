"""Tests for diff grouping and chunking engine."""

from __future__ import annotations

import pytest

from devlensx.review.chunking import (
    calculate_diff_churn,
    estimate_diff_tokens,
    group_diffs,
    parse_diff_files,
)

SAMPLE_MULTI_DIFF = """diff --git a/backend/main.py b/backend/main.py
--- a/backend/main.py
+++ b/backend/main.py
@@ -1,5 +1,6 @@
 import os
+import sys
 def run():
-    print("running")
+    print("running devlensx")
diff --git a/backend/api.py b/backend/api.py
--- a/backend/api.py
+++ b/backend/api.py
@@ -10,3 +10,4 @@
 def get_data():
+    return {"ok": True}
diff --git a/frontend/App.tsx b/frontend/App.tsx
--- a/frontend/App.tsx
+++ b/frontend/App.tsx
@@ -1,2 +1,3 @@
 export function App() {
+  return <div>App</div>;
 }
"""


def test_calculate_diff_churn():
    diff = """
+added 1
+added 2
-deleted 1
 unchanged
"""
    added, deleted, churn = calculate_diff_churn(diff)
    assert added == 2
    assert deleted == 1
    assert churn == 3


def test_estimate_diff_tokens():
    diff = "\n".join([f"+line {i}" for i in range(10)])
    tok = estimate_diff_tokens(diff)
    assert tok > 350  # base overhead + lines


def test_parse_diff_files():
    files = parse_diff_files(SAMPLE_MULTI_DIFF)
    assert len(files) == 3
    assert files[0].path == "backend/main.py"
    assert files[1].path == "backend/api.py"
    assert files[2].path == "frontend/App.tsx"
    assert files[0].churn == 3  # +sys, -print, +print


def test_group_diffs_small_change():
    files = parse_diff_files(SAMPLE_MULTI_DIFF)
    groups = group_diffs(files, small_change_max_files=5, small_change_max_churn=500)
    assert len(groups) == 1
    assert groups[0].label == "small change set"
    assert len(groups[0].files) == 3


def test_group_diffs_large_partitioning():
    files = parse_diff_files(SAMPLE_MULTI_DIFF)
    # Force partition by setting small_change_max_files=1
    groups = group_diffs(files, small_change_max_files=1)
    assert len(groups) >= 2
    labels = [g.label for g in groups]
    assert any("backend" in l for l in labels)
    assert any("frontend" in l for l in labels)
