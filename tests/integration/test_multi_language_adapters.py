"""
DevLensX Integration Test Suite: Multi-Language URM Execution (Java, TypeScript, Python)
Verifies that Java, TypeScript (sp-portfolio), and Python files parse into concrete URMSymbol objects and relationships.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.urm.adapters.java_adapter import JavaLanguageAdapter
from devlensx.urm.adapters.typescript_adapter import TypeScriptLanguageAdapter
from devlensx.urm.adapters.python_adapter import PythonLanguageAdapter


def test_multi_language_adapters():
    print("Executing Integration Test: Multi-Language URM Adapters (Java, TypeScript, Python)...")

    # 1. Java Adapter Verification
    java_src = """
    package org.samples.petclinic.owner;
    import org.springframework.web.bind.annotation.RestController;
    
    @RestController
    public class OwnerController {
        private final OwnerRepository ownerRepository;
        public OwnerController(OwnerRepository ownerRepository) {
            this.ownerRepository = ownerRepository;
        }
    }
    """
    from devlensx.shared.types import SupportedLanguage
    from devlensx.parser.treesitter_parser import get_treesitter_parser
    java_adapter = JavaLanguageAdapter()
    assert java_adapter.can_parse("OwnerController.java")
    parser = get_treesitter_parser()
    java_result = parser.parse_file_from_source("OwnerController.java", java_src)
    java_symbols = java_adapter.extract_symbols(java_result)
    assert len(java_symbols) >= 1
    assert java_symbols[0].language == "java"
    print(f"  🟢 Java URM Adapter Verified: Discovered '{java_symbols[0].name}' ({java_symbols[0].language})")

    # 2. TypeScript / Next.js Adapter Verification (sp-portfolio)
    ts_src = """
    import { ThemeProvider } from './theme-provider';
    export function SPDevProvider({ children }: { children: React.ReactNode }) {
        return <ThemeProvider>{children}</ThemeProvider>;
    }
    export interface PortfolioConfig {
        theme: string;
    }
    """
    ts_adapter = TypeScriptLanguageAdapter()
    assert ts_adapter.can_parse("src/context/spdev-provider.tsx")
    ts_result = parser.parse_file_from_source("src/context/spdev-provider.tsx", ts_src)
    ts_symbols = ts_adapter.extract_symbols(ts_result)
    assert len(ts_symbols) >= 2
    ts_names = [s.name for s in ts_symbols]
    assert "SPDevProvider" in ts_names
    assert "PortfolioConfig" in ts_names
    assert ts_symbols[0].language == "typescript"
    print(f"  🟢 TypeScript URM Adapter Verified: Discovered '{ts_names[0]}' & '{ts_names[1]}' ({ts_symbols[0].language})")

    # 3. Python / FastAPI Adapter Verification
    py_src = """
    from fastapi import APIRouter
    router = APIRouter()
    
    class UserService:
        def get_user(self, user_id: int):
            return {"user_id": user_id}
            
    @router.get("/users")
    def list_users():
        return []
    """
    py_adapter = PythonLanguageAdapter()
    assert py_adapter.can_parse("user_service.py")
    py_result = parser.parse_file_from_source("user_service.py", py_src)
    py_symbols = py_adapter.extract_symbols(py_result)
    assert len(py_symbols) >= 2
    py_names = [s.name for s in py_symbols]
    assert "UserService" in py_names
    assert "list_users" in py_names
    print(f"  🟢 Python URM Adapter Verified: Discovered '{py_names[0]}' & '{py_names[-1]}' ({py_symbols[0].language})")

    print("Integration Test Multi-Language URM Adapters Complete: 100% Passed\n")


if __name__ == "__main__":
    test_multi_language_adapters()
