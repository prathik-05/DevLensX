"""Multi-language reasoning regression: no Spring claims on TS/Python, correct branching."""
from devlensx.deep_reasoning import (
    DeepReasoningEngine, build_deep_reasoning, simple_name, is_prod_component,
    build_method_index, prod_methods,
)
from devlensx.codereview import CodeRabbitEngine, ReviewConfig
import pytest
import devlensx.deep_reasoning

@pytest.fixture(autouse=True)
def disable_external_llm(monkeypatch):
    monkeypatch.setattr(devlensx.deep_reasoning, "get_llm_provider", None)


TS_MODEL = {
    "repo": "portfolio", "repo_summary": {"language": "typescript", "framework": "React Context", "build_system": "npm"},
    "classes": [
        {"name": "Home", "stereotype": "Component", "kind": "function", "file": "app/page.tsx",
         "line_start": 1, "line_end": 60, "annotations": [], "metadata": {}},
        {"name": "CertCard", "stereotype": "Component", "kind": "function", "file": "card.tsx",
         "line_start": 1, "line_end": 80, "annotations": [], "metadata": {}},
        {"name": "useSPDev", "stereotype": "Hook", "kind": "function", "file": "ctx.tsx",
         "line_start": 1, "line_end": 30, "annotations": [], "metadata": {}},
        {"name": "CertCardProps", "stereotype": "Interface", "kind": "interface", "file": "types.ts",
         "line_start": 1, "line_end": 10, "annotations": [], "metadata": {}},
        {"name": "POST", "stereotype": "Function", "kind": "function", "file": "src/app/api/contact/route.ts",
         "line_start": 1, "line_end": 20, "annotations": [], "metadata": {}},
    ],
    "relationships": [{"source": "Home", "target": "CertCard", "type": "DEPENDS_ON"}],
    "endpoints": [],
}

PY_MODEL = {
    "repo": "battleship", "repo_summary": {"language": "python", "framework": "", "build_system": "Unknown"},
    "classes": [
        {"name": "Game", "stereotype": "Class", "kind": "class", "file": "game.py",
         "line_start": 1, "line_end": 90, "annotations": [], "metadata": {}},
        {"name": "__init__", "stereotype": "Constructor", "kind": "constructor", "file": "game.py",
         "line_start": 5, "line_end": 10, "annotations": [], "is_test": False,
         "metadata": {"parent_class": "py_Game_1", "parameters": [{"name": "board_size", "type": ""}]}},
        {"name": "Ship", "stereotype": "Class", "kind": "class", "file": "ship.py",
         "line_start": 1, "line_end": 40, "annotations": [], "metadata": {}},
        {"name": "__len__", "stereotype": "DunderMethod", "kind": "method", "file": "ship.py",
         "line_start": 12, "line_end": 14, "annotations": [], "metadata": {"parent_class": "py_Ship_2"}},
        {"name": "TestGame", "stereotype": "Test", "kind": "class", "file": "test_game.py",
         "line_start": 1, "line_end": 30, "annotations": [], "is_test": True, "metadata": {}},
    ],
    "relationships": [],
    "endpoints": [],
}

JAVA_MODEL = {
    "repo": "shop", "repo_summary": {"language": "java", "framework": "Spring Boot", "build_system": "Maven"},
    "classes": [
        {"name": "OrderController", "stereotype": "Controller", "kind": "class", "file": "OrderController.java",
         "line_start": 1, "line_end": 120, "annotations": ["Controller", "RequestMapping"], "metadata": {}},
        {"name": "create", "stereotype": "Method", "kind": "method", "file": "OrderController.java",
         "line_start": 40, "line_end": 60, "annotations": ["PostMapping"], "is_test": False,
         "metadata": {"parent_class": "java_OrderController_1", "parameters": [{"name": "order", "type": "Order"}]}},
        {"name": "WelcomeController", "stereotype": "Controller", "kind": "class", "file": "Welcome.java",
         "line_start": 1, "line_end": 20, "annotations": ["Controller"], "metadata": {}},
        {"name": "Order", "stereotype": "Entity", "kind": "class", "file": "Order.java",
         "line_start": 1, "line_end": 80, "annotations": ["Entity", "Table"], "metadata": {}},
        {"name": "OrderRepository", "stereotype": "Repository", "kind": "interface", "file": "OrderRepository.java",
         "line_start": 1, "line_end": 20, "annotations": ["Repository"], "metadata": {}},
    ],
    "relationships": [{"source": "java_OrderController_1", "target": "OrderRepository", "type": "DEPENDS_ON"}],
    "endpoints": [
        {"route": "/orders", "method": "POST", "handler": "java_OrderController_create_1"},
        {"route": "/", "method": "GET", "handler": "java_WelcomeController_index_2"},
    ],
}


def test_simple_name_multilang_prefix():
    assert simple_name("java_OwnerController_345") == "OwnerController"
    assert simple_name("py_AIPlayer_1") == "AIPlayer"
    assert simple_name("java_OwnerController_initCreationForm_351") == "OwnerController_initCreationForm"
    assert simple_name("OwnerController") == "OwnerController"


def test_component_filter_excludes_dunder_and_parented_functions():
    assert is_prod_component({"name": "Game", "stereotype": "Class", "kind": "class"}) is True
    assert is_prod_component({"name": "__len__", "stereotype": "DunderMethod", "kind": "method"}) is False
    assert is_prod_component({"name": "Home", "stereotype": "Component", "kind": "function", "metadata": {}}) is True
    assert is_prod_component({"name": "helper", "stereotype": "Function", "kind": "function",
                              "metadata": {"parent_class": "py_mod_1"}}) is False
    assert is_prod_component({"name": "TestGame", "stereotype": "Test", "kind": "class", "is_test": True}) is False


def test_method_index_includes_parented_functions():
    idx = build_method_index(PY_MODEL["classes"])
    assert "Game" in idx
    assert any(m["is_ctor"] for m in idx["Game"])


def test_typescript_purpose_and_no_spring():
    ctx, narratives = build_deep_reasoning(TS_MODEL, None, [])
    blob = " ".join(narratives.values())
    for banned in ["@Valid", "@Transactional", "JPA", "Spring", "Lombok", "constructor injection"]:
        assert banned not in blob, f"Spring leak in TS narrative: {banned}"
    assert "POST /api/contact" in narratives["purpose"]
    assert "components" in narratives["purpose"]
    # Behavioral units rank above pure interfaces
    names = [c["name"] for c in ctx.key_components]
    assert names.index("Home") < names.index("CertCardProps")
    assert any("Hook" in p or "hooks" in p.lower() for p in ctx.architectural_patterns)


def test_python_purpose_and_no_di_claim():
    ctx, narratives = build_deep_reasoning(PY_MODEL, None, [])
    blob = " ".join(narratives.values())
    for banned in ["@Valid", "@Transactional", "JPA", "Spring", "Dependency Injection"]:
        assert banned not in blob, f"Spring leak in Python narrative: {banned}"
    assert "Game" in narratives["purpose"]
    assert ctx.total_classes == 2  # Game + Ship only


def test_java_validation_gating():
    eng = CodeRabbitEngine(ReviewConfig(provider="none"))
    ctx = {"repo": "shop", "language": "java", "classes": JAVA_MODEL["classes"],
           "relationships": JAVA_MODEL["relationships"], "endpoints": JAVA_MODEL["endpoints"]}
    findings = eng._repo_aware_findings(ctx["classes"], ctx["relationships"], ctx["endpoints"], language="java")
    titles = " ".join(f["title"] for f in findings)
    # POST /orders takes input -> flagged; static GET / welcome page -> not flagged
    assert "OrderController" in titles
    assert "WelcomeController" not in titles


def test_python_no_spring_findings():
    eng = CodeRabbitEngine(ReviewConfig(provider="none"))
    findings = eng._repo_aware_findings(PY_MODEL["classes"], [], [], language="python")
    blob = " ".join(f["title"] + f["description"] for f in findings)
    for banned in ["@Valid", "@Transactional", "BindingResult", "ControllerAdvice"]:
        assert banned not in blob
