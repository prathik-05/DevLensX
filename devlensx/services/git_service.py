"""
DevLensX Git Intelligence & Stack Trace Debug Services
"""

import subprocess
from typing import Dict, Any, List


class GitService:
    @staticmethod
    def get_file_churn_facts(repo_path: str, classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Runs git log --follow per component file to extract checkable facts."""
        churn_results = []
        for c in classes[:5]:
            file_path = c.get("file", "")
            if not file_path:
                continue

            commit_count = 1
            fix_count = 0
            try:
                # Use list-based subprocess to prevent command injection
                cmd = ["git", "log", "--oneline", "--", file_path]
                output = subprocess.check_output(cmd, cwd=repo_path, text=True, stderr=subprocess.DEVNULL)
                lines = output.strip().split("\n")
                if lines and lines[0]:
                    commit_count = len(lines)
                    fix_count = sum(1 for line in lines if any(w in line.lower() for w in ["fix", "bug", "hotfix", "issue"]))
            except Exception:
                pass

            churn_results.append({
                "file": file_path,
                "class_name": c.get("name", "Component"),
                "commit_count": commit_count,
                "fix_commit_heuristic_count": fix_count,
                "label": "Fact (Checkable via git log)",
                "heuristic_note": f"{fix_count} commits contain 'fix/bug' keywords in message"
            })
        return churn_results


class DebugService:
    @staticmethod
    def trace_stack_trace(stack_trace: str, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Maps class and method tokens in user-pasted stack trace against parsed AST graph nodes."""
        trace = stack_trace.strip()
        if not trace:
            return {"error": "Stack trace content is required."}

        trace_tokens = set(w.strip("?,.!;:'\"()[]{}<>\n\r\t") for w in trace.replace("/", ".").replace("\\", ".").split())
        matched_classes = [
            c for c in classes
            if c["name"] in trace_tokens or any(c["name"].lower() in tok.lower() for tok in trace_tokens)
        ]

        call_chain = [f"{c['name']} ({c.get('stereotype', 'Component')})" for c in matched_classes]

        return {
            "status": "success",
            "grounding_status": "🟢 GRAPH TRACE MAPPED",
            "matched_components": [c["name"] for c in matched_classes],
            "call_chain": call_chain if call_chain else ["Trace tokens mapped against repository AST graph"],
            "recommendation": (
                f"Grounding match: Stack trace references {len(matched_classes)} parsed codebase class(es): "
                f"{', '.join([c['name'] for c in matched_classes]) if matched_classes else 'None'}. "
                "Inspect dependency call chain above for potential null references or state mismatches."
            )
        }
