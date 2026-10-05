"""Build planner — orchestrates Impact + BuildStudioEngine, snapshot-bound."""

from typing import Dict, Any
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.impact.analyzer import ImpactAnalyzer
from devlensx.build.change_plan import ChangePlan, BuildStep


class BuildPlanner:
    @staticmethod
    def plan(task: str, target_symbol: str, analysis_run_id: str) -> ChangePlan:
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            raise ValueError(f"UNKNOWN_RUN:{analysis_run_id}")
        impact = ImpactAnalyzer.analyze(target_symbol, analysis_run_id)
        if impact.status == "TARGET_NOT_FOUND" or not impact.direct:
            raise ValueError(f"TARGET_NOT_FOUND:{target_symbol}")
        # Reuse existing BuildStudioEngine for textual plan
        steps: list[BuildStep] = []
        # Step 1: the target itself — AI_SUGGESTION (proposed edit)
        steps.append(BuildStep(
            file=impact.direct[0].get("file",""), symbol=target_symbol, operation="MODIFY",
            reason=f"Modify {target_symbol} to implement: {task}",
            depends_on=[d["symbol"] for d in impact.downstream[:2]],
            risk="MEDIUM", status="AI_SUGGESTION",
        ))
        # Downstream steps — also suggestions
        for d in impact.downstream[:3]:
            steps.append(BuildStep(
                file=d.get("file",""), symbol=d["symbol"], operation="MODIFY",
                reason=f"Propagate change from {target_symbol} to {d['symbol']}",
                depends_on=[target_symbol], risk="LOW", status="AI_SUGGESTION"
            ))
        # Tests
        for t in impact.tests[:2]:
            steps.append(BuildStep(
                file=t.get("file",""), symbol=t["symbol"], operation="MODIFY",
                reason=f"Update test {t['symbol']} to reflect new behavior",
                depends_on=[target_symbol], risk="LOW", status="AI_SUGGESTION"
            ))
        # Verified facts about existing code (for evidence)
        verified_refs = impact.evidence_refs
        return ChangePlan(
            repository_id=snap.repository_id,
            analysis_run_id=snap.analysis_run_id,
            commit_hash=snap.commit_hash,
            task=task,
            steps=steps,
            evidence_refs=verified_refs,
        )