import time, json, pathlib
from typing import List, Dict, Any
from devlensx.evaluation.models import GoldenCase
from devlensx.evaluation.dataset import load_dataset, save_dataset, generate_default_dataset
from devlensx.evaluation.evaluator import GoldenEvaluator
from devlensx.evaluation.report import generate_report

class GoldenRunner:
    @staticmethod
    def ensure_dataset():
        cases = load_dataset()
        if not cases:
            cases = generate_default_dataset()
        return cases

    @staticmethod
    def _ensure_analyzed(case: GoldenCase):
        # Ensure repository is analyzed and we have a run_id
        from devlensx.evidence.resolver import get_snapshot_registry
        from devlensx.chat.orchestrator import store_model
        from devlensx.repository_memory import RepositoryIntelligenceEngine
        from pathlib import Path
        reg = get_snapshot_registry()
        # Find existing run for repo
        for snap in reg._snapshots.values():
            if snap.repository_id == case.repository:
                # Reuse
                return snap.analysis_run_id
        # Analyze
        repo_path = case.repository_path or f"eval_repos/{case.repository}"
        if not Path(repo_path).exists():
            return None
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intel.model
        from devlensx.understanding.model.repository_brain import RepositoryBrain
        brain = RepositoryBrain(repo_path, model.get("classes", []))
        import subprocess
        commit = None
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True, timeout=5)
            if r.returncode==0: commit = r.stdout.strip()[:12]
        except: pass
        from devlensx.evidence.resolver import register_snapshot
        snap = register_snapshot(model.get("repo", Path(repo_path).name), brain.analysis_run_id, repo_path, commit)
        store_model(brain.analysis_run_id, model)
        return brain.analysis_run_id

    @staticmethod
    def run_case(case: GoldenCase) -> Dict[str, Any]:
        run_id = GoldenRunner._ensure_analyzed(case)
        if not run_id:
            return {"answer": "", "claims": [], "evidence_refs": [], "analysis_run_id": "", "error": "no repo"}
        from devlensx.chat.orchestrator import ChatOrchestrator
        try:
            ans = ChatOrchestrator.chat(run_id, case.question, mode=case.mode)
            # For AI_SUGGESTION cases, chat may return INSUFFICIENT; we also check workspace Build path
            # For simplicity, return ans directly
            result = ans.to_dict() if hasattr(ans, "to_dict") else ans
            result["analysis_run_id"] = run_id
            return result
        except Exception as e:
            return {"answer": "", "claims": [], "evidence_refs": [], "analysis_run_id": run_id, "error": str(e)}

    @staticmethod
    def run_all(cases: List[GoldenCase] = None) -> Dict[str, Any]:
        if cases is None:
            cases = GoldenRunner.ensure_dataset()
        results = []
        passed = 0
        failed = 0
        for c in cases:
            res = GoldenRunner.run_case(c)
            ev = GoldenEvaluator.evaluate(c, res)
            ev["result"] = res
            results.append(ev)
            if ev["passed"]: passed+=1
            else: failed+=1
        report = generate_report(cases, results)
        return report

if __name__ == "__main__":
    from devlensx.evaluation.report import save_report
    cases = GoldenRunner.ensure_dataset()
    report = GoldenRunner.run_all(cases)
    save_report(report)
    print(json.dumps(report, indent=2))
