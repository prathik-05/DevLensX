"""
Unit tests for Wiki diagram grounding and individual claim verification in DevLensX.
Verifies:
- Data layer and state management diagrams return empty list when no data models exist (no arbitrary 8-symbol fallback).
- Relationship edges are filtered strictly to the page's symbol scope.
- Individual claims are verified against symbol context, preventing false-positive verified badges.
"""

from unittest.mock import MagicMock
import pytest
from devlensx.understanding.documentation.models import DocumentationPage, PageType
from devlensx.understanding.documentation.page_generator import PageGenerator
from devlensx.urm.models import URMRelationship, RelationshipType


@pytest.fixture
def page_generator():
    brain_mock = MagicMock()
    # Mock relationships between A->B and X->Y
    rel1 = URMRelationship(
        source_id="Board",
        target_id="Cell",
        relationship_type=RelationshipType.CALLS,
        language="Java",
    )
    rel_unrelated = URMRelationship(
        source_id="UnrelatedX",
        target_id="UnrelatedY",
        relationship_type=RelationshipType.DEPENDS_ON,
        language="Java",
    )
    brain_mock.relationships = [rel1, rel_unrelated]
    return PageGenerator(brain_mock)


def test_no_arbitrary_fallback_for_data_layer_without_models(page_generator):
    """When a repository has no data layer/entities, Data Layer diagram must be empty, not 8 random symbols."""
    page = DocumentationPage(
        id="data_layer",
        title="Data Layer",
        slug="data-layer",
        page_type=PageType.DATA_LAYER,
    )
    evidence_context = {
        "symbols": {
            "GameController": {"file": "GameController.java", "stereotype": "Controller"},
            "GameView": {"file": "GameView.java", "stereotype": "View"},
            "MinimaxEngine": {"file": "MinimaxEngine.java", "stereotype": "Service"},
        }
    }
    diagrams = page_generator._generate_diagrams(page, evidence_context)
    assert diagrams == [], "Must return empty diagram list when no data layer symbols exist"


def test_data_layer_diagram_generated_when_models_present(page_generator):
    """When data models exist, Data Layer diagram must be generated with data-scoped symbols."""
    page = DocumentationPage(
        id="data_layer",
        title="Data Layer",
        slug="data-layer",
        page_type=PageType.DATA_LAYER,
    )
    evidence_context = {
        "symbols": {
            "Board": {"file": "Board.java", "stereotype": "Entity"},
            "Cell": {"file": "Cell.java", "stereotype": "Model"},
            "GameController": {"file": "GameController.java", "stereotype": "Controller"},
        }
    }
    diagrams = page_generator._generate_diagrams(page, evidence_context)
    assert len(diagrams) == 1
    assert diagrams[0]["diagram_type"] == "DATA_FLOW"
    assert "Board" in diagrams[0]["node_citations"]
    assert "Cell" in diagrams[0]["node_citations"]
    assert "GameController" not in diagrams[0]["node_citations"]


def test_relationships_strictly_filtered_to_page_scope(page_generator):
    """Relationships included in a diagram must only connect symbols present on that page."""
    page = DocumentationPage(
        id="core_arch",
        title="Core Architecture",
        slug="core-architecture",
        page_type=PageType.CORE_ARCHITECTURE,
    )
    evidence_context = {
        "symbols": {
            "Board": {"file": "Board.java", "stereotype": "Entity"},
            "Cell": {"file": "Cell.java", "stereotype": "Model"},
        }
    }
    diagrams = page_generator._generate_diagrams(page, evidence_context)
    assert len(diagrams) == 1
    mermaid_code = diagrams[0]["mermaid_code"]
    assert "Board" in mermaid_code
    assert "Cell" in mermaid_code
    assert "UnrelatedX" not in mermaid_code
    assert "UnrelatedY" not in mermaid_code


def test_individual_claim_verification(page_generator):
    """Sections with mixed verified and ungrounded statements must report PARTIALLY_VERIFIED, not VERIFIED."""
    evidence_context = {
        "symbols": {
            "Board": {"file": "Board.java", "line_start": 10, "line_end": 50},
        }
    }
    content = (
        "The Board class encapsulates game cell operations and state transitions.\n"
        "The distributed clustering manager balances traffic across ten secondary nodes.\n"
    )
    result = page_generator._verify_section_claims(content, evidence_context)
    assert result["overall_verdict"] == "PARTIALLY_VERIFIED"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["symbol"] == "Board"
    claims = result["claims"]
    assert any(c["verdict"] == "VERIFIED" and c["symbol"] == "Board" for c in claims)
    assert any(c["verdict"] == "UNVERIFIED" for c in claims)
