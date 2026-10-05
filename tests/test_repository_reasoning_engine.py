import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devlensx.reasoning.engine import RepositoryReasoningEngine


def test_manifest_extraction_with_maven():
    engine = RepositoryReasoningEngine()
    fake_model = {
        "root_path": "eval_repos/spring-petclinic",
        "classes": [{"file": "src/main/java/Foo.java", "name": "Foo"}],
        "repo_summary": {"language": "Java", "framework": "Spring Boot"}
    }
    instructions = engine.extract_manifest_instructions(fake_model)
    assert instructions["has_manifest"] is True
    assert "pom.xml" in instructions["manifests"]
    assert instructions["install"] == "mvn clean install -DskipTests"
    assert instructions["test"] == "mvn test"
    assert "mvn spring-boot:run" in instructions["run"]


def test_manifest_extraction_fail_closed_when_no_manifest():
    engine = RepositoryReasoningEngine()
    fake_model = {
        "root_path": "/nonexistent/repo",
        "classes": [{"file": "scratch.txt", "name": "Scratch"}],
        "repo_summary": {}
    }
    instructions = engine.extract_manifest_instructions(fake_model)
    assert instructions["has_manifest"] is False
    assert instructions["manifests"] == []
    assert instructions["install"] is None
    assert instructions["run"] is None
    assert instructions["test"] is None


def test_explain_architecture_grounding():
    engine = RepositoryReasoningEngine()
    fake_model = {
        "repo": "demo-backend",
        "classes": [
            {"name": "UserController", "stereotype": "Controller", "file": "UserController.java"},
            {"name": "UserService", "stereotype": "Service", "file": "UserService.java"},
            {"name": "UserRepository", "stereotype": "Repository", "file": "UserRepository.java"},
            {"name": "UserEntity", "stereotype": "Entity", "file": "UserEntity.java"}
        ],
        "relationships": [
            {"source": "UserController", "target": "UserService", "type": "DEPENDS_ON"},
            {"source": "UserService", "target": "UserRepository", "type": "DEPENDS_ON"}
        ],
        "repo_summary": {"language": "Java", "framework": "Spring"}
    }
    res = engine.explain_architecture(fake_model)
    assert res["repository"] == "demo-backend"
    assert "Layered" in res["inferred_style"]
    assert len(res["observed_layers"]) >= 3
    assert len(res["observed_flow"]) >= 2
    assert res["verdict"] == "VERIFIED_GROUNDING"
    assert res["inference_label"] == "INFERRED_SUGGESTION"
    assert "UserController" in res["observed_flow"][0]


def test_explain_symbol_grounding():
    engine = RepositoryReasoningEngine()
    fake_model = {
        "classes": [
            {
                "name": "OrderController",
                "file": "src/controllers/OrderController.java",
                "line_start": 15,
                "line_end": 75,
                "stereotype": "Controller",
                "injected_dependencies": ["OrderService"],
                "methods": [{"name": "getOrder"}, {"name": "createOrder"}]
            }
        ]
    }
    explanation = engine.explain_symbol(
        symbol_name_or_file="OrderController",
        action="what_does_this_do",
        repo_model=fake_model
    )
    assert explanation.symbol_name == "OrderController"
    assert explanation.file_path == "src/controllers/OrderController.java"
    assert explanation.line_start == 15
    assert explanation.line_end == 75
    assert explanation.action == "what_does_this_do"
    assert explanation.verdict == "VERIFIED"
    assert len(explanation.citations) == 1
    assert "src/controllers/OrderController.java#L15-L75" == explanation.citations[0]
    assert any(d["dependency"] == "OrderService" for d in explanation.outgoing_dependencies)


def test_wiki_overview_generation():
    engine = RepositoryReasoningEngine()
    fake_model = {
        "repo": "employee-api",
        "classes": [
            {"name": "EmpController", "stereotype": "Controller", "file": "EmpController.java"},
            {"name": "EmpService", "stereotype": "Service", "file": "EmpService.java"},
            {"name": "EmpRepository", "stereotype": "Repository", "file": "EmpRepository.java"}
        ],
        "repo_summary": {"language": "Java", "framework": "Spring Boot"}
    }
    sections = engine.generate_wiki_overview(fake_model)
    assert len(sections) >= 5
    headings = [s["heading"] for s in sections]
    assert any("What This Repository Is" in h for h in headings)
    assert any("Architecture" in h for h in headings)
    assert any("Technology Stack" in h for h in headings)
    assert any("Key Components" in h for h in headings)
    for s in sections:
        assert "documents the role and implementation of" not in s["content"].lower()
