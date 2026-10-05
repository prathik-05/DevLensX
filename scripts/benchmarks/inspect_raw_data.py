import json

print("=" * 80)
print("RAW GROUND TRUTH AUDIT OF SAVED BENCHMARK DATASETS")
print("=" * 80)

for fname in ['eval_dataset_spring-petclinic.json', 'eval_dataset_mybatis-3.json', 'eval_dataset_dubbo.json']:
    with open(fname, 'r', encoding='utf-8') as f:
        data = json.load(f)
    repo = data['repository']
    findings = data['findings_evaluation_dataset']
    print(f"\n--- {repo} ({fname}) ---")
    print(f"Total findings in sample: {len(findings)}")
    print(f"Recorded Timings (ms): {data.get('timing_benchmarks_ms')}")
    
    tp_cnt = 0
    fp_cnt = 0
    pending_cnt = 0
    v_cnt = 0
    r_cnt = 0
    
    for f_idx, item in enumerate(findings):
        lbl = item.get('manual_ground_truth_label', 'UNSET')
        verdict = item.get('critic_verdict', 'UNSET')
        cat = item.get('category', 'UNSET')
        score = item.get('evidence_coverage_score', 0.0)
        ratio = item.get('evidence_ratio', '0/4')
        fid = item.get('finding_id', f'F-{f_idx}')
        title = item.get('title', '')
        
        if lbl == 'TP': tp_cnt += 1
        elif lbl == 'FP': fp_cnt += 1
        elif lbl == 'PENDING': pending_cnt += 1
        
        if verdict == 'VERIFIED': v_cnt += 1
        elif verdict == 'REJECTED': r_cnt += 1
        
        print(f"  [{fid}] LBL={lbl:7s} | VERDICT={verdict:8s} | Score={score:4.1f}% ({ratio}) | Cat={cat:18s} | {title[:40]}")
    
    print(f"\nSummary for {repo}:")
    print(f"  Labels: TP={tp_cnt}, FP={fp_cnt}, PENDING={pending_cnt}")
    print(f"  Critic Verdicts: VERIFIED={v_cnt}, REJECTED={r_cnt}")
