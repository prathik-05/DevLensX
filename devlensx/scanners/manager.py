"""
DevLensX Scanner & Plugin Manager (P6-B)

Provides a unified orchestrator for all static scanners, external linters, and context packagers
(ast-grep, Semgrep, Repomix, Tree-sitter).

HARD INVARIANTS:
1. No external scanner directly awards VERIFIED status.
2. Scanners emit CandidateFinding objects tagged with an explicit ScannerStatus.
3. Every finding is bound to (repository_id, analysis_run_id, commit_hash).
"""

import sys
import shutil
import subprocess
import argparse
from typing import List, Dict, Any, Optional
from devlensx.scanners.base import BaseScanner, CandidateFinding, ScannerStatus
from devlensx.scanners.semgrep_scanner import SemgrepScanner
from devlensx.scanners.astgrep_scanner import AstGrepScanner
from devlensx.scanners.repomix_adapter import RepomixAdapter


class ScannerManager:
    """Orchestrates external scanner plugins and native adapters."""

    def __init__(self):
        self.scanners: Dict[str, BaseScanner] = {
            "ast-grep": AstGrepScanner(),
            "semgrep": SemgrepScanner(),
            "repomix": RepomixAdapter(),
        }

    def register_scanner(self, name: str, scanner: BaseScanner):
        self.scanners[name] = scanner

    def get_status(self) -> Dict[str, Any]:
        """Returns health and installation status of all registered scanner plugins."""
        result = {}
        for name, scanner in self.scanners.items():
            installed = scanner.is_installed()
            binary_path = None
            if hasattr(scanner, "_resolve_binary"):
                binary_path = scanner._resolve_binary()
            elif hasattr(scanner, "_resolve_semgrep"):
                binary_path = scanner._resolve_semgrep()

            result[name] = {
                "name": name,
                "installed": installed,
                "enabled": scanner.enabled,
                "binary_path": binary_path,
                "type": "cli_adapter",
            }
        return result

    def install_plugin(self, name: str) -> Dict[str, Any]:
        """
        Attempts automated installation of the specified scanner/tool via npm or pip.
        """
        name_lower = name.lower()
        if name_lower in ("ast-grep", "sg"):
            cmd = ["npm", "install", "-g", "@ast-grep/cli"]
        elif name_lower == "repomix":
            cmd = ["npm", "install", "-g", "repomix"]
        elif name_lower == "semgrep":
            cmd = [sys.executable, "-m", "pip", "install", "semgrep"]
        else:
            return {
                "plugin": name,
                "status": "ERROR",
                "message": f"Unknown plugin '{name}'. Supported plugins: ast-grep, repomix, semgrep"
            }

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            success = proc.returncode == 0
            return {
                "plugin": name,
                "status": "SUCCESS" if success else "FAILED",
                "stdout": proc.stdout[-500:] if proc.stdout else "",
                "stderr": proc.stderr[-500:] if proc.stderr else "",
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {
                "plugin": name,
                "status": "ERROR",
                "message": str(e)
            }

    def scan_all(
        self,
        repo_path: str,
        repository_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        commit_hash: Optional[str] = None
    ) -> List[CandidateFinding]:
        """
        Runs all enabled scanners against repo_path and aggregates CandidateFinding items.
        """
        all_findings: List[CandidateFinding] = []
        for name, scanner in self.scanners.items():
            if not scanner.enabled:
                continue
            try:
                findings = scanner.scan(
                    repo_path=repo_path,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash
                )
                all_findings.extend(findings)
            except Exception as e:
                all_findings.append(
                    CandidateFinding(
                        finding_id=f"{name.upper()}-EXEC-ERROR",
                        tool=name,
                        check_id=f"{name}.execution.error",
                        file=repo_path,
                        message=f"Error executing scanner '{name}': {str(e)}",
                        status=ScannerStatus.ERROR,
                        repository_id=repository_id,
                        analysis_run_id=analysis_run_id,
                        commit_hash=commit_hash,
                    )
                )
        return all_findings


def main():
    parser = argparse.ArgumentParser(description="DevLensX Scanner & Plugin CLI")
    parser.add_argument("--status", action="store_true", help="Display scanner plugin installation status")
    parser.add_argument("--install", nargs="+", help="Install plugins (e.g. --install ast-grep repomix semgrep)")
    parser.add_argument("--scan", type=str, help="Scan a repository path with all available scanners")
    args = parser.parse_args()

    manager = ScannerManager()

    if args.install:
        for tool in args.install:
            print(f"Installing {tool}...")
            res = manager.install_plugin(tool)
            print(f"Result for {tool}: {res.get('status')} (Code: {res.get('returncode')})")

    if args.status or not (args.install or args.scan):
        status = manager.get_status()
        print("\n=== DevLensX Scanner & Plugin Status ===")
        for name, info in status.items():
            inst_str = "[INSTALLED]" if info["installed"] else "[NOT INSTALLED]"
            print(f" - {name:<12} {inst_str:<16} Path: {info['binary_path']}")
        print()

    if args.scan:
        print(f"Scanning {args.scan}...")
        findings = manager.scan_all(args.scan)
        print(f"Completed scan. {len(findings)} candidate findings reported.")
        for f in findings:
            print(f" [{f.status.value}] ({f.tool}) {f.check_id}: {f.message[:80]}")


if __name__ == "__main__":
    main()
