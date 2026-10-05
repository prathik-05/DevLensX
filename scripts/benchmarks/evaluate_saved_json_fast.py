"""
Fast Saved JSON Dataset Re-Evaluation Script
Loads exact finding objects from saved eval_dataset_*.json files
and evaluates pre-fix critic_verdict vs post-fix critic_verdict.
"""
import json, os, sys
sys.path.insert(0, os.getcwd())

from devlensx.parser import parse_repo
from devlensx.graph import KuzuGraphStore
from devlensx.critic import CriticAgent

datasets = [
    ("Spring PetClinic", "eval_dataset_spring-petclinic.json", "eval_repos/spring-petclinic"),
    ("MyBatis 3", "eval_dataset_mybatis-3.json", "eval_repos/mybatis-3"),
]

print("==========================================================================================")
print("FAST SAVED JSON DATASET RE-VERIFICATION (PRE-FIX VS POST-FIX VERDICTS)")
print("==========================================================================================")

for name, json_file, repo_path in datasets:
    if not os.path.exists(json_file) or not os.path.exists(repo_path):
        continue

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = data.get("findings_evaluation_dataset", [])
    model = parse_repo(repo_path)
    graph = KuzuGraphStore(db_path=f"fast_db_{name.replace(' ', '_')}")
    graph.build_from_model(model)
    critic = CriticAgent(graph)

    matches = 0
    mismatches = 0

    for item in findings:
        finding_obj = {
            "title": item["title"],
            "agent": item["agent"],
            "category": item["category"],
            "severity": item["severity"],
            "class_name": item["class_name"],
            "file": item["file"],
            "claim": item["claim"],
            "evidence": {}
        }
        res = critic.verify_finding(finding_obj, model)
        pre_v = item["critic_verdict"]
        post_v = res["verdict"]
        if pre_v == post_v:
            matches += 1
        else:
            mismatches += 1
            print(f"  MISMATCH [{name}] {item['finding_id']}: {item['title']} | Pre: {pre_v} -> Post: {post_v}")

    print(f"[+] {name}: Saved Dataset Findings={len(findings)} | Exact Verdict Matches={matches}/{len(findings)} | Discrepancies={mismatches}")

print("==========================================================================================")
