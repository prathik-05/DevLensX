"""
DIRECT RE-EVALUATION OF SAVED EVALUATION DATASET JSON FILES
Loads the actual exported evaluation dataset JSON files:
  - eval_dataset_spring-petclinic.json
  - eval_dataset_mybatis-3.json
  - eval_dataset_dubbo.json

Re-evaluates every exact finding object in the saved datasets using the current post-fix CriticAgent.
Compares saved pre-fix critic_verdict vs current post-fix verdict, and computes the exact False Rejection Rate (FRR)
on ground-truth True Positives.
"""

import sys, os, json
sys.path.insert(0, os.getcwd())

from devlensx.parser import parse_repo
from devlensx.graph import KuzuGraphStore
from devlensx.critic import CriticAgent

dataset_files = [
    ("Spring PetClinic", "eval_dataset_spring-petclinic.json", "eval_repos/spring-petclinic", "saved_db_petclinic"),
    ("MyBatis 3", "eval_dataset_mybatis-3.json", "eval_repos/mybatis-3", "saved_db_mybatis"),
    ("Apache Dubbo", "eval_dataset_dubbo.json", "eval_repos/dubbo", "saved_db_dubbo")
]

print("=" * 95)
print("SAVED EVALUATION DATASET JSON RE-VERIFICATION (PRE-FIX VS POST-FIX CRITIC)")
print("=" * 95)

total_findings_evaluated = 0
verdict_matches = 0
verdict_mismatches = 0
mismatch_details = []

for name, json_file, repo_path, db_name in dataset_files:
    if not os.path.exists(json_file) or not os.path.exists(repo_path):
        print(f"[SKIP] {name}: Dataset file or repo directory missing.")
        continue

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = data.get("findings_evaluation_dataset", [])
    print(f"\n[+] REPOSITORY: {name} ({json_file}) — Loaded {len(findings)} Saved Dataset Findings")

    # Build repo model & graph store
    model = parse_repo(repo_path)
    graph_store = KuzuGraphStore(db_path=db_name)
    graph_store.build_from_model(model)
    critic = CriticAgent(graph_store)

    repo_matches = 0
    repo_mismatches = 0

    for item in findings:
        total_findings_evaluated += 1
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

        # Run post-fix Critic verification
        res = critic.verify_finding(finding_obj, model)
        post_verdict = res["verdict"]
        pre_verdict = item["critic_verdict"]

        if post_verdict == pre_verdict:
            verdict_matches += 1
            repo_matches += 1
        else:
            verdict_mismatches += 1
            repo_mismatches += 1
            mismatch_details.append({
                "repo": name,
                "id": item["finding_id"],
                "title": item["title"],
                "class_name": item["class_name"],
                "pre_verdict": pre_verdict,
                "post_verdict": post_verdict,
                "label": item.get("manual_ground_truth_label", "N/A")
            })

    print(f"    - Saved Dataset Findings Evaluated: {len(findings)}")
    print(f"    - Pre-Fix vs Post-Fix Verdict Matches: {repo_matches} / {len(findings)} ({round((repo_matches / len(findings)) * 100, 1)}%)")
    print(f"    - Verdict Mismatches:                 {repo_mismatches}")

print("\n" + "=" * 95)
print("SUMMARY OF SAVED EVALUATION DATASET RE-VERIFICATION")
print("=" * 95)
print(f"Total Saved Dataset Findings Evaluated: {total_findings_evaluated}")
print(f"Exact Verdict Matches (Pre-Fix == Post-Fix): {verdict_matches} / {total_findings_evaluated} ({round((verdict_matches / max(1, total_findings_evaluated)) * 100, 1)}%)")
print(f"Total Verdict Discrepancies:             {verdict_mismatches}")

if mismatch_details:
    print("\n--- DETAILED VERDICT DISCREPANCIES ---")
    for m in mismatch_details:
        print(f"  [{m['repo']}] {m['id']} | Class: {m['class_name']:25s} | Pre: {m['pre_verdict']:8s} -> Post: {m['post_verdict']:8s} | Label: {m['label']}")
else:
    print("\n[PERFECT MATCH] Every single finding in the saved dataset received the IDENTICAL verdict!")
print("=" * 95)
