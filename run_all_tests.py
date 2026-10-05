"""
DevLensX Master Regression Test Suite Runner (Step 7)
Runs Unit, Integration, Adversarial, and End-to-End Developer Journey Test Suites.
"""

import sys
import os
import subprocess
sys.stdout.reconfigure(encoding="utf-8")

def run_suite():
    print("=========================================================================")
    print("🚀 DEVLENSX STEP 7: MASTER AUTOMATED REGRESSION TEST SUITE")
    print("=========================================================================\n")

    test_scripts = [
        "tests/unit/test_security.py",
        "tests/unit/test_brain.py",
        "tests/unit/test_session_memory.py",
        "tests/unit/test_feature_memory.py",
        "tests/unit/test_git_memory.py",
        "tests/unit/test_multi_user_isolation.py",
        "tests/unit/test_debug_service.py",
        "tests/unit/test_build_studio_service.py",
        "tests/unit/test_health_observability.py",
        "tests/unit/test_urm.py",
        "tests/unit/test_urm_stabilization.py",
        "tests/unit/test_deepwiki_line_citations.py",
        "tests/unit/test_claim_verifier.py",
        "tests/unit/test_diagram_model.py",
        "tests/unit/test_dependency_diagram.py",
        "tests/unit/test_component_diagram.py",
        "tests/unit/test_architecture_diagram.py",
        "tests/unit/test_call_graph.py",
        "tests/unit/test_data_flow.py",
        "tests/unit/test_sequence_diagram.py",
        "tests/unit/test_diagram_provenance.py",
        "tests/unit/test_hybrid_retriever.py",
        "tests/unit/test_documentation_planner.py",
        "tests/unit/test_documentation_evidence_scope.py",
        "tests/unit/test_documentation_retriever.py",
        "tests/unit/test_documentation_claims.py",
        "tests/unit/test_documentation_verification.py",
        "tests/unit/test_documentation_citations.py",
        "tests/unit/test_documentation_cache.py",
        "tests/unit/test_documentation_evidence_invariants.py",
        "tests/unit/test_deepwiki_chat_engine.py",
        "tests/integration/test_multi_language_adapters.py",
        "tests/integration/test_step3_real_repositories.py",
        "tests/integration/test_workspace_integration.py",
        "tests/integration/test_live_llm_integration.py",
        "tests/integration/test_unsupported_language_boundary.py",
        "tests/integration/test_wiki_petclinic.py",
        "tests/integration/test_wiki_typescript.py",
        "tests/integration/test_wiki_python.py",
        "tests/integration/test_documentation_repository_isolation.py",
        "tests/integration/test_documentation_llm_fallback.py",
        "tests/performance/test_performance_benchmarks.py",
        "tests/e2e/test_phase12_browser_journey.py",
        "tests/e2e/test_d6_diagram_browser_journey.py",
        "tests/e2e/test_d7_documentation_browser_journey.py",
        "tests/test_critic_adversarial.py",
        "tests/test_documentation_adversarial.py",
        "tests/test_step6_developer_journey.py",
        "tests/security/test_runtime_security.py",
        "tests/test_step10_staging_validation.py"
    ]

    passed = 0
    total = len(test_scripts)

    for script in test_scripts:
        print(f"--- Running Test Module: {script} ---")
        cmd = [sys.executable, script]
        res = subprocess.run(cmd, cwd=os.getcwd(), capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0:
            passed += 1
            print(f"🟢 {script} PASSED")
        else:
            print(f"🔴 {script} FAILED:")
            print(res.stderr or res.stdout)
            sys.exit(1)
        print()

    print("=========================================================================")
    print(f"🟢 DEVLENSX REGRESSION TEST SUITE PASSED: {passed}/{total} currently implemented regression suites passed.")
    print("=========================================================================")

if __name__ == "__main__":
    run_suite()
