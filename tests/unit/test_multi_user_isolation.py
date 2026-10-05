"""
DevLensX Unit Test Suite: Multi-User RepositoryBrain Snapshot Isolation
Verifies that Repository A and Repository B maintain distinct, isolated Brain snapshots.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.understanding.model.repository_brain import RepositoryBrain
from devlensx.services.analysis_service import brain_registry, AnalysisService


def test_multi_user_repository_isolation():
    print("Executing Unit Test: Multi-User RepositoryBrain Isolation...")

    # Repo A: Spring PetClinic
    classes_a = [{"name": "OwnerController", "package": "org.petclinic.owner", "stereotype": "Controller"}]
    brain_a = RepositoryBrain("eval_repos/spring-petclinic", classes_a)
    brain_registry[brain_a.analysis_run_id] = brain_a

    # Repo B: MyBatis-3
    classes_b = [{"name": "SqlSession", "package": "org.apache.mybatis", "stereotype": "Service"}]
    brain_b = RepositoryBrain("eval_repos/mybatis-3", classes_b)
    brain_registry[brain_b.analysis_run_id] = brain_b

    # Verify Isolation
    assert brain_a.analysis_run_id != brain_b.analysis_run_id, "Analysis run ID collision!"
    
    res_a = AnalysisService.get_brain_by_run_id(brain_a.analysis_run_id)
    res_b = AnalysisService.get_brain_by_run_id(brain_b.analysis_run_id)

    assert res_a.symbols == ["OwnerController"]
    assert res_b.symbols == ["SqlSession"]
    assert res_a.repo_path != res_b.repo_path

    print(f"  🟢 Multi-User Isolation Passed (Repo A: {brain_a.analysis_run_id}, Repo B: {brain_b.analysis_run_id})")
    print("Unit Test Multi-User Isolation Complete: 100% Passed\n")


if __name__ == "__main__":
    test_multi_user_repository_isolation()
