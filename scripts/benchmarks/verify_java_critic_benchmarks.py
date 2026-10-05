"""
JAVA EVALUATION BENCHMARK VERIFICATION (ISOLATED GRAPH DBs)
Re-runs the full DevLensX pipeline (Parser -> Graph -> Agents -> Critic)
on all three evaluation repositories (Spring PetClinic, MyBatis-3, Apache Dubbo)
to confirm that the Critic fix did NOT alter the baseline Java evaluation metrics.
"""

import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devlensx.parser.java_parser import parse_repo
from devlensx.graph.kuzu_store import KuzuGraphStore
from devlensx.agents.architecture_agent import ArchitectureAgent
from devlensx.agents.security_agent import SecurityAgent
from devlensx.agents.change_impact_agent import ChangeImpactAgent
from devlensx.critic.critic_engine import CriticAgent

eval_targets = [
    ("spring-petclinic", "eval_repos/spring-petclinic", "graph_db_petclinic"),
    ("mybatis-3", "eval_repos/mybatis-3", "graph_db_mybatis"),
    ("dubbo", "eval_repos/dubbo", "graph_db_dubbo")
]

print("=" * 80)
print("DEVLENSX JAVA BENCHMARK RE-VERIFICATION POST-CRITIC FIX")
print("=" * 80)

for name, target_path, db_name in eval_targets:
    if not os.path.exists(target_path):
        print(f"\n[SKIP] {name}: Directory '{target_path}' not found locally.")
        continue

    print(f"\n" + "-" * 80)
    print(f"EVALUATING: {name} ({target_path})")
    print("-" * 80)

    # Stage 1: Parse AST
    model = parse_repo(target_path)
    stats = model.get("stats", {})

    print(f"  Parsed Classes:               {stats.get('classes_found', 0)}")
    print(f"  Parsed Methods:               {stats.get('methods_found', 0)}")
    print(f"  Parsed REST Endpoints:        {stats.get('endpoints_found', 0)}")
    print(f"  Has Java Capability:          {stats.get('has_java_capability', False)}")

    # Stage 2: Graph Store with isolated db path
    graph = KuzuGraphStore(db_path=db_name)
    edge_stats = graph.build_from_model(model)
    print(f"  Graph Edge Stats:             {edge_stats}")

    # Stage 3: Multi-Agent Scans
    arch = ArchitectureAgent(graph)
    sec = SecurityAgent()
    impact = ChangeImpactAgent(graph)

    arch_res = arch.analyze(model)
    sec_res = sec.analyze(model, target_path, language="java")
    impact_res = impact.analyze(model)

    raw_findings = arch_res["findings"] + sec_res["findings"] + impact_res["findings"]
    print(f"  Raw Agent Findings:           {len(raw_findings)}")

    # Stage 4: Critic Verification
    critic = CriticAgent(graph)
    verified = critic.verify_all(raw_findings, model)

    verified_count = sum(1 for v in verified if v["verdict"] == "VERIFIED")
    rejected_count = sum(1 for v in verified if v["verdict"] == "REJECTED")
    avg_evidence_score = round(sum(v["evidence_coverage_score"] for v in verified) / len(verified), 1) if verified else 0.0

    print(f"\n  CRITIC VERDICT SUMMARY:")
    print(f"    Verified Findings:          {verified_count}")
    print(f"    Rejected Findings:          {rejected_count}")
    print(f"    Grounding Rate:             {round((verified_count / len(verified)) * 100, 1) if verified else 0.0}%")
    print(f"    Mean Evidence Coverage:     {avg_evidence_score}%")

    print(f"\n  SAMPLE FINDINGS BREAKDOWN (Top 5):")
    for i, v in enumerate(verified[:5]):
        print(f"    [{v['verdict']:8s}] [{v['evidence_coverage_score']:5.1f}% ({v['evidence_ratio']})] [{v['category']:18s}] {v['title']}")
        trail = v["evidence_trail"]
        print(f"               Graph: {trail['graph_check']['passed']} | AST: {trail['ast_check']['passed']} | Semgrep: {trail['semgrep_check']['passed']} | Struct: {trail['structural_check']['passed']}")

print("\n" + "=" * 80)
print("BENCHMARK RE-VERIFICATION COMPLETE")
print("=" * 80)
