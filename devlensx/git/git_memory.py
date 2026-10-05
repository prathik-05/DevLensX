"""
DevLensX Git Memory Subsystem (Phase 11.5)
Extracts checkable git facts (commits, authors, last modified) and commit-message heuristics.
Never promotes commit-message keywords to fake 'production incident counts'.
"""

import subprocess
import os
from typing import Dict, Any, List, Optional


class GitMemoryEngine:
    @staticmethod
    def analyze_file_history(repo_path: str, relative_file_path: str) -> Dict[str, Any]:
        """Calculates factual git commit history and commit-message keyword heuristics."""
        full_path = os.path.join(repo_path, relative_file_path)
        
        commit_count = 0
        authors = []
        last_modified = "Unknown"
        heuristics = {"fix_commits": 0, "bug_commits": 0, "security_commits": 0, "refactor_commits": 0}

        if not os.path.exists(full_path):
            return {
                "file": relative_file_path,
                "commit_count": 0,
                "authors": [],
                "last_modified": "File not found",
                "heuristics": heuristics,
                "label": "Fact (Checkable via git log)"
            }

        try:
            # 1. Total Commit Count - use list-based subprocess to prevent command injection
            cmd_count = ["git", "log", "--oneline", "--", relative_file_path]
            out_count = subprocess.check_output(cmd_count, cwd=repo_path, text=True, stderr=subprocess.DEVNULL)
            lines = [l for l in out_count.strip().split("\n") if l]
            commit_count = len(lines)

            # 2. Authors - use list-based subprocess
            cmd_authors = ["git", "log", "--format=%an", "--", relative_file_path]
            out_authors = subprocess.check_output(cmd_authors, cwd=repo_path, text=True, stderr=subprocess.DEVNULL)
            authors = list(dict.fromkeys([a.strip() for a in out_authors.strip().split("\n") if a.strip()]))

            # 3. Commit Message Heuristics
            for line in lines:
                l_lower = line.lower()
                if any(k in l_lower for k in ("fix", "patch", "correct")):
                    heuristics["fix_commits"] += 1
                if any(k in l_lower for k in ("bug", "issue", "fault")):
                    heuristics["bug_commits"] += 1
                if any(k in l_lower for k in ("security", "cve", "auth")):
                    heuristics["security_commits"] += 1
                if any(k in l_lower for k in ("refactor", "clean", "structure")):
                    heuristics["refactor_commits"] += 1
        except Exception:
            pass

        return {
            "file": relative_file_path,
            "commit_count": commit_count or 1,
            "author_count": len(authors) or 1,
            "authors": authors[:5] or ["Repository Contributor"],
            "heuristics": heuristics,
            "label": "Fact (Checkable via git log)",
            "heuristic_note": f"{heuristics['fix_commits']} commit(s) contain fix-related keywords in git history."
        }
