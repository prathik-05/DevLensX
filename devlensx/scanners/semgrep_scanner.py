"""
DevLensX Semgrep CE Scanner Adapter (P6-B)

Executes Semgrep Community Edition when available on host.
Emits normalized CandidateFinding objects with explicit execution statuses:
  - EXECUTED_MATCH: Semgrep executed and found static rule violations
  - EXECUTED_NO_MATCH: Semgrep executed cleanly with 0 violations
  - NOT_INSTALLED: Binary not present on host PATH
  - SKIPPED: Scanner disabled by configuration
  - ERROR: Subprocess execution failed or timed out
"""

import shutil
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from devlensx.scanners.base import BaseScanner, CandidateFinding, ScannerStatus


class SemgrepScanner(BaseScanner):
    """Adapter for Semgrep Community Edition CLI."""

    def __init__(self, enabled: bool = True, timeout_seconds: int = 45):
        super().__init__(name="semgrep", enabled=enabled)
        self.timeout_seconds = timeout_seconds

    def is_installed(self) -> bool:
        return shutil.which("semgrep") is not None

    def scan(
        self,
        repo_path: str,
        repository_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        commit_hash: Optional[str] = None,
        config: str = "auto"
    ) -> List[CandidateFinding]:
        if not self.enabled:
            return [
                CandidateFinding(
                    finding_id="SEMGREP-SKIPPED",
                    tool="semgrep",
                    check_id="semgrep.scanner.skipped",
                    file=repo_path,
                    message="Semgrep scanner execution skipped by configuration.",
                    status=ScannerStatus.SKIPPED,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        if not self.is_installed():
            return [
                CandidateFinding(
                    finding_id="SEMGREP-NOT-INSTALLED",
                    tool="semgrep",
                    check_id="semgrep.binary.not_installed",
                    file=repo_path,
                    message="Semgrep binary not installed on host PATH. Scan omitted.",
                    status=ScannerStatus.NOT_INSTALLED,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        try:
            cmd = ["semgrep", f"--config={config}", "--json", "--quiet", repo_path]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )

            if proc.returncode in (0, 1): # 0 = clean or findings, 1 = findings reported
                data = json.loads(proc.stdout) if proc.stdout else {}
                results = data.get("results", [])
                
                if not results:
                    return [
                        CandidateFinding(
                            finding_id="SEMGREP-CLEAN",
                            tool="semgrep",
                            check_id="semgrep.scan.clean",
                            file=repo_path,
                            message="Semgrep scan executed: 0 rule violations detected.",
                            status=ScannerStatus.EXECUTED_NO_MATCH,
                            repository_id=repository_id,
                            analysis_run_id=analysis_run_id,
                            commit_hash=commit_hash,
                        )
                    ]

                findings = []
                for idx, item in enumerate(results, 1):
                    findings.append(
                        CandidateFinding(
                            finding_id=f"SEMGREP-{idx:03d}",
                            tool="semgrep",
                            check_id=item.get("check_id", "semgrep.rule"),
                            file=item.get("path", repo_path),
                            line=item.get("start", {}).get("line"),
                            line_range=f"{item.get('start', {}).get('line')}-{item.get('end', {}).get('line')}",
                            message=item.get("extra", {}).get("message", "Semgrep security finding"),
                            severity=str(item.get("extra", {}).get("severity", "MEDIUM")).upper(),
                            category="Semgrep Violation",
                            status=ScannerStatus.EXECUTED_MATCH,
                            repository_id=repository_id,
                            analysis_run_id=analysis_run_id,
                            commit_hash=commit_hash,
                            raw_payload=item,
                        )
                    )
                return findings

            # Non-zero return code (error)
            return [
                CandidateFinding(
                    finding_id="SEMGREP-ERROR",
                    tool="semgrep",
                    check_id="semgrep.execution.error",
                    file=repo_path,
                    message=f"Semgrep execution exited with code {proc.returncode}: {proc.stderr[:200]}",
                    status=ScannerStatus.ERROR,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        except subprocess.TimeoutExpired:
            return [
                CandidateFinding(
                    finding_id="SEMGREP-TIMEOUT",
                    tool="semgrep",
                    check_id="semgrep.execution.timeout",
                    file=repo_path,
                    message=f"Semgrep execution timed out after {self.timeout_seconds}s.",
                    status=ScannerStatus.ERROR,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]
        except Exception as e:
            return [
                CandidateFinding(
                    finding_id="SEMGREP-EXCEPTION",
                    tool="semgrep",
                    check_id="semgrep.execution.exception",
                    file=repo_path,
                    message=f"Semgrep scanner encountered exception: {str(e)}",
                    status=ScannerStatus.ERROR,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]
