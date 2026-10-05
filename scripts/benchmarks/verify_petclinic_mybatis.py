"""
Fast Java Benchmark Verification (PetClinic + MyBatis-3)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devlensx.parser.java_parser import parse_repo
from devlensx.graph.kuzu_store import KuzuGraphStore
from devlensx.agents.architecture_agent import ArchitectureAgent
from devlensx.agents.security_agent import SecurityAgent
from devlensx.agents.change_impact_agent import ChangeImpactAgent
from devlensx.critic.critic_engine import CriticAgent

for name, target_path in [("spring-petclinic", "eval_repos/spring-petclinic"), ("mybatis-3", "eval_repos/mybatis-3")]:
    print("=" * 80)
    print(f"EVALUATING: {name}")
    print("=" * 80)

    model = parse_repo(target_path)
    stats = model.get("stats", {})

    print(f"  Parsed Classes:   {stats.get('classes_found', 0)}")
    print(f"  Parsed Methods:   {stats.get('methods_found', 0)}")

    graph = KuzuGraphStore()
    edge_stats = graph.build_from_model(model)

    arch = ArchitectureAgent(graph)
    sec = SecurityAgent()
    impact = ChangeImpactAgent(graph)

    arch_res = arch.analyze(model)
    sec_res = sec.analyze(model, target_path, language="java")
    impact_res = impact.analyze(model)

    raw_findings = arch_res["findings"] + sec_res["findings"] + impact_res["findings"]
    critic = CriticAgent(graph)
    verified = critic.verify_all(raw_findings, model)

    verified_count = sum(1 for v in verified if v["verdict"] == "VERIFIED")
    rejected_count = sum(1 for v in verified if v["verdict"] == "REJECTED")

    print(f"  Raw Findings:     {len(raw_findings)}")
    print(f"  VERIFIED:         {verified_count}")
    print(f"  REJECTED:         {rejected_count}")
    print(f"  Grounding Rate:   {round((verified_count / len(verified)) * 100, 1) if verified else 0.0}%")
    print()
    for i, v in enumerate(verified):
        print(f"    [{v['verdict']:8s}] [{v['evidence_coverage_score']:5.1f}% ({v['evidence_ratio']})] [{v['category']:18s}] {v['title']}")
        trail = v["evidence_trail"]
        print(f"               Graph: {trail['graph_check']['passed']} | AST: {trail['ast_check']['passed']} | Semgrep: {trail['semgrep_check']['passed']} | Struct: {trail['structural_check']['passed']}")
