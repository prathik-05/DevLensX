"""
DevLensX Unit Test Suite: Dynamic Documentation Planner
Verifies adaptive Wiki navigation trees, bounded evidence scopes, and capability detection.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.understanding.documentation.planner import DocumentationPlanner, plan_documentation
from devlensx.understanding.model.repository_brain import RepositoryBrain
from devlensx.understanding.documentation.models import CapabilityFlag


def test_documentation_planner():
    print("Executing Unit Test: Dynamic Documentation Planner...")

    # Create a mock RepositoryBrain with sp-portfolio-like data
    # Multiple classes per domain to trigger feature detection
    classes = [
        # Theme domain
        {
            "name": "SPDevProvider",
            "stereotype": "Context",
            "file": "src/context/spdev-provider.tsx",
            "line_start": 10,
            "line_end": 50,
            "package": "src.context",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": ["ThemeProvider"],
        },
        {
            "name": "ThemeProvider",
            "stereotype": "Component",
            "file": "src/components/theme-provider.tsx",
            "line_start": 5,
            "line_end": 30,
            "package": "src.components.theme",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": [],
        },
        {
            "name": "ThemeToggle",
            "stereotype": "Component",
            "file": "src/components/theme/ThemeToggle.tsx",
            "line_start": 1,
            "line_end": 40,
            "package": "src.components.theme",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": ["ThemeProvider"],
        },
        # Navigation domain
        {
            "name": "Navbar",
            "stereotype": "Component",
            "file": "src/components/navbar.tsx",
            "line_start": 1,
            "line_end": 100,
            "package": "src.components.navigation",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": ["SPDevProvider"],
        },
        {
            "name": "CommandCenter",
            "stereotype": "Component",
            "file": "src/components/navigation/CommandCenter.tsx",
            "line_start": 1,
            "line_end": 80,
            "package": "src.components.navigation",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": ["Navbar"],
        },
        # Portfolio data domain
        {
            "name": "portfolio",
            "stereotype": "Component",
            "file": "src/data/portfolio.ts",
            "line_start": 1,
            "line_end": 200,
            "package": "src.data",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": [],
        },
        {
            "name": "certifications",
            "stereotype": "Component",
            "file": "src/data/certifications.ts",
            "line_start": 1,
            "line_end": 100,
            "package": "src.data",
            "is_test": False,
            "endpoints": [],
            "injected_dependencies": [],
        },
        # API domain
        {
            "name": "OwnerController",
            "stereotype": "Controller",
            "file": "src/app/api/contact/route.ts",
            "line_start": 1,
            "line_end": 50,
            "package": "src.app.api.contact",
            "is_test": False,
            "endpoints": [{"path": "/api/contact", "method": "POST"}],
            "injected_dependencies": [],
        },
        {
            "name": "ProjectsController",
            "stereotype": "Controller",
            "file": "src/app/api/projects/route.ts",
            "line_start": 1,
            "line_end": 60,
            "package": "src.app.api.projects",
            "is_test": False,
            "endpoints": [{"path": "/api/projects", "method": "GET"}],
            "injected_dependencies": [],
        },
    ]

    brain = RepositoryBrain(
        repo_path="eval_repos/sp-portfolio",
        classes=classes,
        analysis_run_id="test_run_123"
    )

    # Plan documentation
    tree = plan_documentation(brain)

    # 1. Verify mandatory pages exist
    mandatory_pages = ["overview", "getting_started", "project_structure", "core_architecture", "glossary"]
    for page_id in mandatory_pages:
        page = tree.get_page(page_id)
        assert page is not None, f"Mandatory page {page_id} missing"
        assert page.is_mandatory == True, f"Page {page_id} should be mandatory"
    print(f"  🟢 All {len(mandatory_pages)} mandatory pages present")

    # 2. Verify conditional pages for TypeScript repo
    page_ids = [p.id for p in tree.pages]
    assert "components" in page_ids, "Components page should exist for TS repo with components"
    assert "features" in page_ids, "Features page should exist when capabilities detected"
    assert "api_routes" in page_ids, "API Routes page should exist when endpoints present"
    assert "state_management" in page_ids, "State Management page should exist for Context/Provider"
    assert "configuration" in page_ids, "Configuration page should exist for package.json/tsconfig"
    conditional_pages = [p for p in page_ids if p not in mandatory_pages]
    print(f"  🟢 Conditional pages correctly detected: {conditional_pages}")

    # 3. Verify evidence scopes are populated
    overview_page = tree.get_page("overview")
    assert overview_page.evidence_scope is not None
    assert len(overview_page.evidence_scope.relevant_symbols) > 0
    assert len(overview_page.evidence_scope.evidence_ids) > 0
    print(f"  🟢 Overview evidence scope: {len(overview_page.evidence_scope.relevant_symbols)} symbols, {len(overview_page.evidence_scope.evidence_ids)} citations")

    components_page = tree.get_page("components")
    assert components_page.evidence_scope is not None
    assert "SPDevProvider" in components_page.evidence_scope.relevant_symbols
    assert "ThemeProvider" in components_page.evidence_scope.relevant_symbols
    assert "Navbar" in components_page.evidence_scope.relevant_symbols
    print(f"  🟢 Components evidence scope correctly bound to component symbols")

    api_page = tree.get_page("api_routes")
    assert api_page.evidence_scope is not None
    assert "OwnerController" in api_page.evidence_scope.relevant_symbols
    print(f"  🟢 API Routes evidence scope correctly bound to controller")

    state_page = tree.get_page("state_management")
    assert state_page.evidence_scope is not None
    assert "SPDevProvider" in state_page.evidence_scope.relevant_symbols
    print(f"  🟢 State Management evidence scope correctly bound to Context/Provider")

    # 4. Verify repository profile
    assert tree.repository_profile is not None
    assert tree.repository_profile.languages in (["TypeScript"], ["TypeScript/JavaScript"])
    assert tree.repository_profile.has_frontend == True
    assert tree.repository_profile.has_api == True
    assert tree.repository_profile.has_state_management == True
    assert CapabilityFlag.HAS_COMPONENTS in tree.repository_profile.capabilities
    assert CapabilityFlag.HAS_STATE_MANAGEMENT in tree.repository_profile.capabilities
    print(f"  🟢 Repository profile correctly derived from evidence")

    # 5. Verify sections are planned for each page
    for page in tree.pages:
        assert len(page.sections) > 0, f"Page {page.id} should have sections"
    print(f"  🟢 All pages have planned sections")

    # 6. Test Java repo (Spring PetClinic style)
    java_classes = [
        {"name": "OwnerController", "stereotype": "Controller", "file": "OwnerController.java", "line_start": 1, "line_end": 50, "package": "org.petclinic.owner", "is_test": False, "endpoints": [{"path": "/owners"}], "injected_dependencies": ["OwnerRepository"]},
        {"name": "OwnerRepository", "stereotype": "Repository", "file": "OwnerRepository.java", "line_start": 1, "line_end": 30, "package": "org.petclinic.owner", "is_test": False, "endpoints": [], "injected_dependencies": []},
        {"name": "Owner", "stereotype": "Entity", "file": "Owner.java", "line_start": 1, "line_end": 40, "package": "org.petclinic.owner", "is_test": False, "endpoints": [], "injected_dependencies": []},
        {"name": "ClinicService", "stereotype": "Service", "file": "ClinicService.java", "line_start": 1, "line_end": 60, "package": "org.petclinic.service", "is_test": False, "endpoints": [], "injected_dependencies": ["OwnerRepository"]},
    ]
    java_brain = RepositoryBrain(repo_path="eval_repos/spring-petclinic", classes=java_classes, analysis_run_id="test_java")
    java_tree = plan_documentation(java_brain)

    java_page_ids = [p.id for p in java_tree.pages]
    assert "components" not in java_page_ids, "Components page should not exist for pure Java backend"
    assert "state_management" not in java_page_ids, "State Management page should not exist for Java"
    assert "data_layer" in java_page_ids, "Data Layer page should exist for Java with entities/repositories"
    print(f"  🟢 Java repo correctly gets Data Layer page, not Components/State Management")

    # 7. Test small repo (minimal pages)
    small_classes = [
        {"name": "Main", "stereotype": "Component", "file": "main.py", "line_start": 1, "line_end": 20, "package": "", "is_test": False, "endpoints": [], "injected_dependencies": []},
    ]
    small_brain = RepositoryBrain(repo_path="eval_repos/tiny-repo", classes=small_classes, analysis_run_id="test_small")
    small_tree = plan_documentation(small_brain)

    small_page_ids = [p.id for p in small_tree.pages]
    # Should only have mandatory pages for tiny repo
    assert len(small_page_ids) == len(mandatory_pages), f"Tiny repo should only get mandatory pages, got: {small_page_ids}"
    print(f"  🟢 Small repo correctly gets only mandatory pages")

    # 8. Verify analysis_run_id is preserved
    assert tree.analysis_run_id == "test_run_123"
    print(f"  🟢 analysis_run_id preserved in documentation tree")

    # 9. Verify no fake pages for unsupported tech
    assert "security" not in small_page_ids, "Security page should not exist without evidence"
    assert "infrastructure" not in small_page_ids, "Infrastructure page should not exist without evidence"
    print(f"  🟢 No fake pages generated without evidence")

    print("\nUnit Test Documentation Planner Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_planner()