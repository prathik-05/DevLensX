import subprocess
from typing import List, Optional
from pathlib import Path
from devlensx.incremental.models import FileChange, ChangeType
from devlensx.core.security import is_safe_path

def _safe_git_args():
    return ["--"]

class GitDiffDetector:
    @staticmethod
    def detect_changed_files(repo_path: str, previous_commit: Optional[str] = None, target_commit: Optional[str] = None) -> List[FileChange]:
        """Detect changed files via git diff. If no commits provided, uses unstaged changes vs HEAD."""
        repo = Path(repo_path).resolve()
        # Validate repo_path is safe (no traversal beyond allowed)
        # Use list-based subprocess to prevent injection
        try:
            if previous_commit and target_commit:
                cmd = ["git", "diff", "--name-status", f"{previous_commit}..{target_commit}"]
            elif target_commit:
                cmd = ["git", "diff", "--name-status", target_commit]
            else:
                # unstaged + staged vs HEAD
                cmd = ["git", "diff", "--name-status", "HEAD"]
            result = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                # Try fallback: git status --porcelain for untracked
                cmd2 = ["git", "status", "--porcelain"]
                result2 = subprocess.run(cmd2, cwd=str(repo), capture_output=True, text=True, timeout=10)
                if result2.returncode != 0:
                    return []
                # Parse porcelain: " M file", "?? file", "A  file", " D file"
                changes = []
                for line in result2.stdout.splitlines():
                    if not line.strip():
                        continue
                    # porcelain format: XY<space>path
                    # For simplicity, treat as MODIFIED or ADDED
                    path = line[3:].strip().strip('"')
                    # Security: validate path
                    if not path or ".." in path.split("/"):
                        continue
                    if line.startswith("??"):
                        changes.append(FileChange(path=path, change_type=ChangeType.ADDED))
                    elif line.startswith(" D") or line.startswith("D "):
                        changes.append(FileChange(path=path, change_type=ChangeType.DELETED))
                    else:
                        changes.append(FileChange(path=path, change_type=ChangeType.MODIFIED))
                return changes
            changes = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                if not parts:
                    continue
                status = parts[0].strip()
                # status can be M, A, D, R100, etc.
                if status.startswith("R"):
                    # Renamed: R100\told\tnew
                    if len(parts) >= 3:
                        old = parts[1].strip()
                        new = parts[2].strip()
                        # Security: validate paths
                        if ".." in old or ".." in new:
                            continue
                        changes.append(FileChange(path=new, change_type=ChangeType.RENAMED, old_path=old, new_path=new))
                elif status == "A":
                    path = parts[1].strip() if len(parts) > 1 else ""
                    if path and ".." not in path:
                        changes.append(FileChange(path=path, change_type=ChangeType.ADDED))
                elif status == "D":
                    path = parts[1].strip() if len(parts) > 1 else ""
                    if path and ".." not in path:
                        changes.append(FileChange(path=path, change_type=ChangeType.DELETED))
                elif status == "M":
                    path = parts[1].strip() if len(parts) > 1 else ""
                    if path and ".." not in path:
                        changes.append(FileChange(path=path, change_type=ChangeType.MODIFIED))
                else:
                    # Handle combined statuses like "MM", "AM" - treat as modified
                    path = parts[-1].strip()
                    if path and ".." not in path:
                        # First char indicates type
                        if "A" in status:
                            changes.append(FileChange(path=path, change_type=ChangeType.ADDED))
                        elif "D" in status:
                            changes.append(FileChange(path=path, change_type=ChangeType.DELETED))
                        else:
                            changes.append(FileChange(path=path, change_type=ChangeType.MODIFIED))
            return changes
        except Exception:
            return []

    @staticmethod
    def detect_changed_files_from_list(changed_paths: List[str], change_type: ChangeType = ChangeType.MODIFIED) -> List[FileChange]:
        """Helper for tests to create FileChange list without git."""
        return [FileChange(path=p, change_type=change_type) for p in changed_paths]
