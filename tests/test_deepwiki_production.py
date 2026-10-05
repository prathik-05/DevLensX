import pytest
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.deep_reasoning import DeepReasoningEngine, build_deep_reasoning

client = TestClient(app)


def test_wiki_provider_status_endpoint():
    resp = client.get("/api/wiki/provider/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "provider" in data
    assert "model" in data
    assert "configured" in data
    assert "offline" in data
    assert isinstance(data["configured"], bool)


def test_wiki_ask_copilot_endpoint():
    payload = {
        "question": "Where is the main entry point and database repository?",
        "page_id": "overview",
        "section_id": "Repository Identity"
    }
    resp = client.post("/api/wiki/test_run_123/ask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == "test_run_123"
    assert data["page_id"] == "overview"
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert "verdict" in data


def test_deep_reasoning_narratives_fallback_clean(monkeypatch):
    import devlensx.deep_reasoning
    monkeypatch.setattr(devlensx.deep_reasoning, "get_llm_provider", None)

    fake_model = {
        "repo": "demo-store",
        "repo_summary": {"language": "Java", "framework": "Spring Boot"},
        "classes": [
            {"name": "OrderController", "stereotype": "Controller", "kind": "class", "file": "OrderController.java", "annotations": ["@Controller"], "is_test": False},
            {"name": "OrderService", "stereotype": "Service", "kind": "class", "file": "OrderService.java", "annotations": ["@Service"], "is_test": False},
            {"name": "OrderRepository", "stereotype": "Repository", "kind": "interface", "file": "OrderRepository.java", "annotations": ["@Repository"], "is_test": False},
            {"name": "OrderEntity", "stereotype": "Entity", "kind": "class", "file": "OrderEntity.java", "annotations": ["@Entity"], "is_test": False},
        ],
        "relationships": [
            {"source": "OrderController", "target": "OrderService", "type": "DEPENDS_ON"},
            {"source": "OrderService", "target": "OrderRepository", "type": "DEPENDS_ON"},
        ],
        "endpoints": [
            {"method": "POST", "path": "/api/orders", "handler": "createOrder"},
            {"method": "GET", "path": "/api/orders/{id}", "handler": "getOrder"},
        ]
    }

    ctx, narratives = build_deep_reasoning(fake_model)
    assert "OrderController" in narratives["purpose"]
    assert "2 HTTP endpoints" in narratives["purpose"]
    assert "Architectural Style" in narratives["architecture"] or "Architecture" in narratives["architecture"]
    assert "OrderController" in narratives["components"]
    assert "Flow 1" in narratives["flow"]
