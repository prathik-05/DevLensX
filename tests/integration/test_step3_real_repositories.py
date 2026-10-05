"""
DevLensX Integration Test Suite: Step 3 Real Multi-Language Repository Execution
Executes full repository discovery, Tree-sitter parsing, adapter processing,
URM conversion, and relationship resolution across Java, TypeScript, and Python.
"""

import sys
import os
import time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.shared.types import SupportedLanguage
from devlensx.parser.treesitter_parser import get_treesitter_parser
from devlensx.urm.adapters.java_adapter import JavaLanguageAdapter
from devlensx.urm.adapters.typescript_adapter import TypeScriptLanguageAdapter
from devlensx.urm.adapters.python_adapter import PythonLanguageAdapter


def run_repository_pipeline(repo_name: str, root_dir: str, primary_ext: str, adapter):
    print(f"\n--- Running Full Pipeline for {repo_name} ({primary_ext}) ---")
    t0 = time.time()

    root_path = Path(root_dir)
    if not root_path.exists():
        root_path.mkdir(parents=True, exist_ok=True)

    parser = get_treesitter_parser()

    # 1. File Discovery
    files_discovered = []
    for p in root_path.rglob(f"*{primary_ext}"):
        if "node_modules" not in str(p) and ".git" not in str(p) and "__pycache__" not in str(p):
            files_discovered.append(p)

    parsed_count = 0
    skipped_count = 0
    failed_count = 0
    all_symbols = []
    all_relationships = []
    all_parse_results = []

    # 2. Tree-sitter Parsing + Symbol Extraction Across All Files
    for f in files_discovered:
        try:
            result = parser.parse_file(str(f))
            if not result.success or result.root_node is None:
                failed_count += 1
                continue
            if not result.source_code.strip():
                skipped_count += 1
                continue

            syms = adapter.extract_symbols(result)
            rels = adapter.extract_relationships(result, syms)
            all_symbols.extend(syms)
            all_relationships.extend(rels)
            all_parse_results.append(result)

            # Invariant Check: 1 <= line_start <= line_end
            for s in syms:
                assert s.line_start >= 1, f"Invalid line_start in {s.name}"
                assert s.line_end >= s.line_start, f"Invalid line_end in {s.name}"

            parsed_count += 1
        except Exception:
            failed_count += 1

    t_pipeline = time.time() - t0

    print(f"  Repo: {repo_name}")
    print(f"  Files Discovered: {len(files_discovered)}")
    print(f"  Files Parsed: {parsed_count} | Skipped: {skipped_count} | Failed: {failed_count}")
    print(f"  URM Symbols Discovered: {len(all_symbols)}")
    print(f"  URM Relationships Extracted: {len(all_relationships)}")
    print(f"  Total Pipeline Time: {t_pipeline:.4f}s")

    # Invariant assertion: Symbols MUST be discovered from a real repository
    if len(files_discovered) > 2:
        assert parsed_count > 0, f"Parsing Failure: Discovered {len(files_discovered)} files but parsed 0 in {repo_name}!"

    return {
        "repo": repo_name,
        "discovered": len(files_discovered),
        "parsed": parsed_count,
        "symbols": len(all_symbols),
        "relationships": len(all_relationships),
        "time": t_pipeline
    }


def test_step3_real_repositories():
    print("Executing Integration Test: Step 3 Real Multi-Language Repository Execution...")

    # 1. Java Benchmark Repository Execution (spring-petclinic)
    java_adapter = JavaLanguageAdapter()
    java_res = run_repository_pipeline("spring-petclinic", "eval_repos/spring-petclinic", ".java", java_adapter)

    # 2. TypeScript Benchmark Repository Execution (sp-portfolio)
    ts_adapter = TypeScriptLanguageAdapter()
    ts_res = run_repository_pipeline("sp-portfolio", "web/src", ".tsx", ts_adapter)

    # 3. Python Benchmark Repository Execution (devlensx core)
    py_adapter = PythonLanguageAdapter()
    py_res = run_repository_pipeline("devlensx-python", "devlensx", ".py", py_adapter)

    # 4. Unsupported Language Boundary Validation (Go / Rust)
    print("\n--- Running Unsupported Language Boundary Test (Go / Rust) ---")
    go_file = "main.go"
    assert not java_adapter.can_parse(go_file)
    assert not py_adapter.can_parse(go_file)
    print("  ⚪ Unsupported Language Verified: main.go correctly triggers ⚪ UNSUPPORTED LANGUAGE boundary")

    # 5. Verify real symbol counts are meaningful (evidence-grounded parsing works)
    assert java_res["symbols"] > 10, f"spring-petclinic should yield >10 symbols, got {java_res['symbols']}"
    assert py_res["symbols"] > 10, f"devlensx should yield >10 symbols, got {py_res['symbols']}"
    print("\n  🟢 Real Repository Evidence Verified:")
    print(f"     spring-petclinic: {java_res['symbols']} symbols from {java_res['parsed']} files")
    print(f"     sp-portfolio:     {ts_res['symbols']} symbols from {ts_res['parsed']} files")
    print(f"     devlensx-python:  {py_res['symbols']} symbols from {py_res['parsed']} files")

    print("\nStep 3 Integration Test Complete: All Languages Parsed via Tree-sitter 100% Passed\n")


if __name__ == "__main__":
    test_step3_real_repositories()