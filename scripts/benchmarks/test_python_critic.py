"""
REAL TEST: Run the Critic Agent directly on sample findings from a Python repo
to evaluate how graph_check, ast_check, semgrep_check, and structural_check perform.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devlensx.parser.java_parser import parse_repo
from devlensx.graph.kuzu_store import KuzuGraphStore
from devlensx.critic.critic_engine import CriticAgent

model = parse_repo("eval_repos/battleship-python")
graph = KuzuGraphStore()
graph.build_from_model(model)
critic = CriticAgent(graph)

# Synthetic findings for the Python repository to evaluate Critic behavior
sample_findings = [
    {
        "agent": "ArchitectureAgent",
        "category": "Maintainability",
        "title": "High Complexity God Class Detected: Board",
        "severity": "HIGH",
        "class_name": "Board",
        "file": "board.py",
        "claim": "Board contains 18 methods, violating single responsibility principles.",
        "evidence": {"method_count": 18, "stereotype": "Other"}
    },
    {
        "agent": "SecurityAgent",
        "category": "Hardcoded Secret",
        "title": "Potential Hardcoded Secret Field: 'db_password' in Game",
        "severity": "HIGH",
        "class_name": "Game",
        "file": "game.py",
        "claim": "Class Game contains field 'db_password' which matches secret naming patterns.",
        "evidence": {"field_name": "db_password", "field_type": "str"}
    },
    {
        "agent": "ArchitectureAgent",
        "category": "Coupling",
        "title": "High Coupling Bottleneck: Game",
        "severity": "MEDIUM",
        "class_name": "Game",
        "file": "game.py",
        "claim": "Game is directly depended on by 4 components.",
        "evidence": {"incoming_dependents": 4, "stereotype": "Other"}
    },
    {
        "agent": "ArchitectureAgent",
        "category": "Coupling",
        "title": "Hallucinated Bottleneck: NonExistentPythonClass",
        "severity": "HIGH",
        "class_name": "NonExistentPythonClass",
        "file": "fake.py",
        "claim": "NonExistentPythonClass has 45 incoming dependencies.",
        "evidence": {}
    }
]

print("=" * 80)
print("CRITIC EVALUATION ON PYTHON FINDINGS")
print("=" * 80)
results = critic.verify_all(sample_findings, model)

for i, v in enumerate(results):
    print(f"\n--- Finding #{i+1}: {v['title']} ---")
    print(f"  Verdict:  {v['verdict']}")
    print(f"  Score:    {v['evidence_coverage_score']}%  ({v['evidence_ratio']})")
    print(f"  Category: {v['category']}")
    print(f"  Class:    {v['class_name']}")
    print(f"  File:     {v['file']}")
    trail = v['evidence_trail']
    print(f"  graph_check:      passed={trail['graph_check']['passed']:5}  {trail['graph_check']['details']}")
    print(f"  ast_check:        passed={trail['ast_check']['passed']:5}  {trail['ast_check']['details']}")
    print(f"  semgrep_check:    passed={trail['semgrep_check']['passed']:5}  {trail['semgrep_check']['details']}")
    print(f"  structural_check: passed={trail['structural_check']['passed']:5}  {trail['structural_check']['details']}")
