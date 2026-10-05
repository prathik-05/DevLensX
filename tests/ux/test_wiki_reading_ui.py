"""Wiki reading-layout UI tests (Part 2): ToC, breadcrumb, search, prev/next, previews, expand."""
import pathlib

WIKI = pathlib.Path("web/src/components/WikiView.tsx").read_text(encoding="utf-8")
CODEMAP = pathlib.Path("web/src/components/CodemapView.tsx").read_text(encoding="utf-8")
CSS = pathlib.Path("web/src/index.css").read_text(encoding="utf-8")


def test_three_zone_layout():
    # Left nav + center reading column + right ToC
    assert "On This Page" in WIKI
    assert "maxWidth" in WIKI and "720px" in WIKI
    assert "lg:col-span-6" in WIKI and "lg:col-span-3" in WIKI


def test_breadcrumb_and_search():
    assert "Jump to page or entity" in WIKI
    assert "searchResults" in WIKI
    assert "aria-label=\"Search wiki pages\"" in WIKI


def test_toc_scrollspy():
    assert "IntersectionObserver" in WIKI
    assert "data-section" in WIKI
    assert "setActiveSection" in WIKI


def test_prev_next_navigation():
    assert "prevPage" in WIKI and "nextPage" in WIKI
    assert 'aria-label="Page navigation"' in WIKI


def test_crosslink_hover_previews():
    assert "CrossLinkedText" in WIKI
    assert "hover" in WIKI.lower()
    assert "click to open" in WIKI.lower()


def test_diagram_expand():
    assert "expandedDiagram" in WIKI
    assert "Expand diagram" in WIKI
    assert 'role="dialog"' in WIKI


def test_prose_typography():
    assert ".dl-prose" in CSS
    assert ".dl-details" in CSS
    assert "74ch" in CSS


def test_codemap_progress():
    assert "Stop " in CODEMAP and "aria-live" in CODEMAP
    assert 'role="progressbar"' in CODEMAP
    assert "NOW TOURING" in CODEMAP
    assert 'aria-label="Previous tour stop"' in CODEMAP
    assert 'aria-label="Next tour stop"' in CODEMAP
