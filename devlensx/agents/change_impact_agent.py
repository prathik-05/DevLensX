"""
DevLensX Module 6: Change Impact & Refactoring Agent

Evaluates technical debt, code smells, and blast-radius change impact
using reverse dependency Cypher graph traversal.
Thresholds:
  - Incoming Dependents > 15 : HIGH Risk
  - Incoming Dependents 5-15 : MEDIUM Risk
  - Incoming Dependents < 5  : LOW Risk
"""

class ChangeImpactAgent:
    def __init__(self, graph_store):
        self.graph_store = graph_store

    def analyze_change_impact(self, target_class_name):
        """
        Calculates downstream blast radius if target_class_name is modified.
        Returns affected classes, controllers, services, database entities, and test suites.
        """
        affected = self.graph_store.query_change_impact(target_class_name) or []

        affected_controllers = [a for a in affected if a.get("stereotype") == "Controller"]
        affected_services = [a for a in affected if a.get("stereotype") == "Service"]
        affected_tests = [a for a in affected if a.get("is_test")]
        
        total_count = len(affected)
        
        # Risk Thresholds
        if total_count >= 15 or len(affected_controllers) >= 3:
            risk_level = "HIGH"
        elif total_count >= 5 or len(affected_controllers) >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "target_class": target_class_name,
            "risk_level": risk_level,
            "total_affected_count": total_count,
            "affected_classes": affected,
            "affected_controllers": affected_controllers,
            "affected_services": affected_services,
            "affected_tests": affected_tests
        }

    def analyze(self, repo_model):
        """Scans all repository components to produce Change Impact & Refactoring findings."""
        findings = []
        blast_rank = self.graph_store.query_blast_radius(limit=5)
        by_name = {c.get("name"): c for c in repo_model.get("classes", [])
                   if isinstance(c, dict) and c.get("name")}

        for item in blast_rank:
            if not isinstance(item, dict) or not item.get("class_name"):
                continue
            impact = self.analyze_change_impact(item["class_name"])
            if impact["risk_level"] in ("HIGH", "MEDIUM"):
                matched = by_name.get(item["class_name"], {})
                findings.append({
                    "agent": "ChangeImpactRefactoringAgent",
                    "category": "Change Impact",
                    "title": f"High Blast-Radius Risk: Modifying {item['class_name']}",
                    "severity": impact["risk_level"],
                    "class_name": item["class_name"],
                    "file": matched.get("file", ""),
                    "claim": f"Modifying {item['class_name']} ({item.get('stereotype', '')}) impacts {impact['total_affected_count']} dependent classes, including {len(impact['affected_controllers'])} API controllers and {len(impact['affected_tests'])} test suites.",
                    "evidence": {
                        "target_class": item["class_name"],
                        "incoming_dependents": item.get("incoming_dependents", 0),
                        "affected_controllers": [c.get("class_name", "") for c in impact["affected_controllers"]],
                        "affected_tests": [t.get("class_name", "") for t in impact["affected_tests"]]
                    }
                })

        return {
            "top_high_impact_classes": blast_rank,
            "findings": findings
        }
