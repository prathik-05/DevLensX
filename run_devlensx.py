"""
DevLensX Main Launcher & CLI Tool

Commands:
    python run_devlensx.py analyze <repo_path> [--test-rejection] -> Runs full CLI analysis pipeline with timing
    python run_devlensx.py query <repo_path> <q>                  -> Executes Hybrid Repository Retrieval Q&A
    python run_devlensx.py api                                    -> Starts FastAPI Backend Server
    python run_devlensx.py web                                    -> Starts React Web Platform Frontend
    python run_devlensx.py dashboard                              -> Launches Streamlit Dashboard UI
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.agents import ArchitectureAgent, SecurityAgent, ChangeImpactAgent
from devlensx.critic import CriticAgent
from devlensx.recommendation import RecommendationEngine
import uvicorn


def main():
    if len(sys.argv) < 2:
        print("DevLensX Platform CLI Launcher")
        print("Usage:")
        print("  python run_devlensx.py analyze <repo_path> [--test-rejection] : Analyze repository from CLI")
        print("  python run_devlensx.py query <repo_path> '<q>'                 : Run Hybrid Retrieval Q&A")
        print("  python run_devlensx.py api                                     : Launch FastAPI REST server")
        print("  python run_devlensx.py web                                     : Launch React Web Platform UI")
        print("  python run_devlensx.py dashboard                               : Launch Streamlit Dashboard")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "analyze":
        repo_path = sys.argv[2] if (len(sys.argv) > 2 and not sys.argv[2].startswith("--")) else "sample_repo"
        test_rejection = "--test-rejection" in sys.argv

        print(f"--- Running DevLensX Analysis on: {repo_path} ---")
        t_start = time.perf_counter()

        # Stages 1-3 are orchestrated by Repository Intelligence.
        intelligence = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intelligence.model
        t_parse = intelligence.timings_ms["parse_ast_ms"]

        summary = model.get("repo_summary", {})
        print(f"[+] Stage 1: Parsed {model['stats']['files_parsed']} source files in {t_parse} ms.")
        print(f"    Summary: {summary.get('controllers', 0)} Controllers, {summary.get('services', 0)} Services, {summary.get('repositories', 0)} Repositories, {summary.get('rest_apis', 0)} REST APIs.")

        graph_store = intelligence.graph_store
        edge_stats = intelligence.graph_edge_stats
        t_graph = intelligence.timings_ms["graph_build_ms"]
        print(f"[+] Stage 2: Knowledge Graph built in {t_graph} ms. DEPENDS_ON Edges={edge_stats['DEPENDS_ON']}")

        # Stage 3: Multi-Agent Scan
        t0 = time.perf_counter()
        arch = ArchitectureAgent(graph_store).analyze(model)
        sec = SecurityAgent().analyze(model, repo_path)
        impact = ChangeImpactAgent(graph_store).analyze(model)

        raw_findings = arch["findings"] + sec["findings"] + impact["findings"]

        if test_rejection:
            print("[!] Injecting synthetic hallucinated finding to verify Critic rejection...")
            raw_findings.append({
                "agent": "ArchitectureAgent",
                "category": "Coupling",
                "title": "Hallucinated Bottleneck: NonExistentPaymentGateway",
                "severity": "HIGH",
                "class_name": "NonExistentPaymentGateway",
                "file": "com/example/gateway/NonExistentPaymentGateway.java",
                "claim": "NonExistentPaymentGateway has 45 incoming dependencies violating structural boundaries.",
                "evidence": {}
            })

        t_agents = round((time.perf_counter() - t0) * 1000, 2)
        print(f"[+] Stage 3: Multi-Agent Analysis finished in {t_agents} ms ({len(raw_findings)} raw findings).")

        # Stage 4: Grounding Verification
        t0 = time.perf_counter()
        critic = CriticAgent(graph_store)
        verified = critic.verify_all(raw_findings, model)
        t_critic = round((time.perf_counter() - t0) * 1000, 2)
        print(f"[+] Stage 4: Critic Grounding Verification finished in {t_critic} ms.")

        # Stage 5: Synthesis
        t0 = time.perf_counter()
        synthesis = RecommendationEngine().synthesize(verified, model)
        t_synthesis = round((time.perf_counter() - t0) * 1000, 2)
        t_total = round((time.perf_counter() - t_start) * 1000, 2)
        print(f"[+] Stage 5: Recommendation Synthesis finished in {t_synthesis} ms.")

        print(f"\n[+] Total Pipeline Benchmark Execution Time: {t_total} ms")

        print("\n==================================================")
        print("  DevLensX Repository Intelligence Score")
        print("==================================================")
        print(f"Overall Score: {synthesis['repository_intelligence_score']['overall']} / 100")
        print(f"Sub-scores: {synthesis['repository_intelligence_score']['sub_scores']}")
        print(f"Sub-score Formulas: {synthesis['repository_intelligence_score']['sub_score_explanations']}")
        print(f"\nVerified Findings (Grounding Confirmed): {synthesis['total_verified_findings']} | Rejected (Hallucinations): {synthesis['total_rejected_findings']}")

        print("\nTop Engineering Recommendations Cards:")
        for rec in synthesis["top_engineering_recommendations"]:
            print(f"  #{rec['rank']} [{rec['priority']}] {rec['title']} (Evidence Coverage Score: {rec['evidence_coverage_score']}% | Ratio: {rec['evidence_summary']})")
            print(f"     Reason: {rec['reason']}")
            print(f"     Effort: {rec['estimated_effort']} | Benefit: {rec['expected_benefit']}")

        if synthesis['total_rejected_findings'] > 0:
            print("\nRejected Findings Feed (Demonstrating Critic Rejection):")
            for rej in synthesis['rejected_findings_sample']:
                print(f"  [X] [{rej['verdict']}] {rej['title']} (Coverage: {rej['evidence_coverage_score']}% | Ratio: {rej['evidence_ratio']})")

    elif cmd == "query":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "sample_repo"
        query_text = sys.argv[3] if len(sys.argv) > 3 else "explain OwnerService"
        print(f"--- Running Hybrid Retrieval for Question: '{query_text}' on {repo_path} ---")
        
        intelligence = RepositoryIntelligenceEngine().analyze(repo_path)
        context = intelligence.retrieve(query_text)
        print("\nRetrieved Hybrid Context (Graph Triples + FAISS Semantic Embeddings):")
        import json
        print(json.dumps(context, indent=2))

    elif cmd == "api":
        print("Launching DevLensX FastAPI Server on http://127.0.0.1:8000 ...")
        uvicorn.run("devlensx.api.main:app", host="127.0.0.1", port=8000, reload=True)

    elif cmd == "web":
        print("Launching DevLensX React Web Platform Frontend...")
        web_dir = str(Path(__file__).parent / "web")
        subprocess.run(["npm", "run", "dev"], cwd=web_dir, shell=True)

    elif cmd == "dashboard":
        print("Launching DevLensX Streamlit Dashboard...")
        dashboard_script = str(Path(__file__).parent / "devlensx" / "dashboard" / "app.py")
        subprocess.run(["streamlit", "run", dashboard_script])

    elif cmd in ("ingest", "digest"):
        source = sys.argv[2] if (len(sys.argv) > 2 and not sys.argv[2].startswith("-")) else "."
        output_file = None
        if "-o" in sys.argv:
            idx = sys.argv.index("-o")
            if idx + 1 < len(sys.argv):
                output_file = sys.argv[idx + 1]
        elif "--output" in sys.argv:
            idx = sys.argv.index("--output")
            if idx + 1 < len(sys.argv):
                output_file = sys.argv[idx + 1]

        try:
            from gitingest import ingest
        except ImportError:
            print("Error: gitingest package not found. Install via pip install -e <path-to-gitingest>")
            sys.exit(1)

        print(f"--- DevLensX GitIngest Codebase Bundler ---")
        print(f"Source: {source}")
        summary, tree, content = ingest(source)
        digest = f"# CODEBASE PROMPT DIGEST FOR LLM\n\n{summary}\n\n## Directory Structure\n{tree}\n\n## Source Code\n{content}\n"

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(digest)
            print(f"[+] Codebase prompt digest saved to: {output_file}")
            print(f"\n{summary.strip()}")
        else:
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass
            print(digest)

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
