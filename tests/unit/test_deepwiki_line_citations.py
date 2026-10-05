"""
DevLensX Unit Test Suite: DeepWiki Line-Level Citations & Hierarchical Navigation
Verifies line-level citations (e.g. OwnerController.java:23-45), hierarchical TOC, and inline Mermaid diagrams per feature cluster page.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.understanding.wiki_generator import WikiGenerator


def test_deepwiki_line_citations():
    print("Executing Unit Test: DeepWiki Line-Level Citations & Navigation...")

    classes = [
        {
            "name": "OwnerController",
            "stereotype": "Controller",
            "package": "org.samples.petclinic.owner",
            "file": "src/main/java/org/samples/petclinic/owner/OwnerController.java",
            "line_start": 23,
            "line_range": "23-45",
            "methods": [{"name": "processFindForm", "line_number": 30}]
        },
        {
            "name": "OwnerRepository",
            "stereotype": "Repository",
            "package": "org.samples.petclinic.owner",
            "file": "src/main/java/org/samples/petclinic/owner/OwnerRepository.java",
            "line_start": 10,
            "line_range": "10-25"
        }
    ]

    wiki = WikiGenerator.generate_living_wiki("eval_repos/spring-petclinic", classes)

    # 1. Verify line citations
    assert "citations" in wiki
    assert len(wiki["citations"]) == 2
    assert wiki["citations"][0]["symbol"] == "OwnerController"
    assert wiki["citations"][0]["line_range"] == "23-45"
    assert "OwnerController.java#L23-45" in wiki["citations"][0]["citation_link"]
    print(f"  🟢 Line-Level Citation Verified: {wiki['citations'][0]['citation_link']}")

    # 2. Verify hierarchical navigation tree
    assert "navigation_tree" in wiki
    assert len(wiki["navigation_tree"]) >= 3
    print(f"  🟢 Hierarchical TOC Verified: {len(wiki['navigation_tree'])} Navigation Items")

    # 3. Verify inline Mermaid diagram
    assert "feature_pages" in wiki
    assert len(wiki["feature_pages"]) > 0
    assert "graph TD" in wiki["feature_pages"][0]["mermaid_diagram"]
    print(f"  🟢 Inline Mermaid Diagram Verified: {wiki['feature_pages'][0]['mermaid_diagram']}")

    print("Unit Test DeepWiki Line-Level Citations Complete: 100% Passed\n")


if __name__ == "__main__":
    test_deepwiki_line_citations()
