"""
DevLensX ast-grep Scanner Adapter (P6-B)

Executes ast-grep CLI when available on host.
Emits normalized CandidateFinding objects with explicit execution statuses:
  - EXECUTED_MATCH: ast-grep executed and reported structural code pattern violations
  - EXECUTED_NO_MATCH: ast-grep executed with 0 pattern matches
  - NOT_INSTALLED: Binary 'ast-grep' or 'sg' not present on host PATH
  - SKIPPED: Scanner disabled by configuration
  - ERROR: Subprocess execution failed, timed out, or produced malformed output
"""

import shutil
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from devlensx.scanners.base import BaseScanner, CandidateFinding, ScannerStatus


class AstGrepScanner(BaseScanner):
    """Adapter for ast-grep CLI (ast-grep / sg)."""

    PINNED_VERSION = "0.51.0"

    def __init__(self, enabled: bool = True, timeout_seconds: int = 30):
        super().__init__(name="ast-grep", enabled=enabled)
        self.timeout_seconds = timeout_seconds
        self._cached_version: Optional[str] = None

    def _resolve_binary(self) -> Optional[str]:
        return shutil.which("ast-grep") or shutil.which("sg") or shutil.which("ast-grep.cmd")

    def is_installed(self) -> bool:
        return self._resolve_binary() is not None

    def get_version(self) -> str:
        """Returns detected CLI version or fallback pinned version."""
        if self._cached_version:
            return self._cached_version
        bin_path = self._resolve_binary()
        if not bin_path:
            return self.PINNED_VERSION
        try:
            proc = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                parts = proc.stdout.strip().split()
                if len(parts) >= 2:
                    self._cached_version = parts[1]
                    return self._cached_version
        except Exception:
            pass
        return self.PINNED_VERSION

    def scan(
        self,
        repo_path: str,
        repository_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        commit_hash: Optional[str] = None,
        rule_config: Optional[str] = None
    ) -> List[CandidateFinding]:
        version_str = self.get_version()

        if not self.enabled:
            return [
                CandidateFinding(
                    finding_id="ASTGREP-SKIPPED",
                    tool="ast-grep",
                    tool_version=version_str,
                    check_id="astgrep.scanner.skipped",
                    file=repo_path,
                    message="ast-grep scanner execution skipped by configuration.",
                    status=ScannerStatus.SKIPPED,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        bin_path = self._resolve_binary()
        if not bin_path:
            return [
                CandidateFinding(
                    finding_id="ASTGREP-NOT-INSTALLED",
                    tool="ast-grep",
                    tool_version=self.PINNED_VERSION,
                    check_id="astgrep.binary.not_installed",
                    file=repo_path,
                    message="ast-grep binary not installed on host PATH. Scan omitted.",
                    status=ScannerStatus.NOT_INSTALLED,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        try:
            cmd = [bin_path, "scan", "--json", repo_path]
            if rule_config:
                cmd.extend(["--config", rule_config])

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )

            if proc.returncode in (0, 1):
                raw_json = proc.stdout.strip()
                try:
                    matches = json.loads(raw_json) if raw_json else []
                except json.JSONDecodeError as jde:
                    return [
                        CandidateFinding(
                            finding_id="ASTGREP-MALFORMED-OUTPUT",
                            tool="ast-grep",
                            tool_version=version_str,
                            check_id="astgrep.malformed.output",
                            file=repo_path,
                            message=f"ast-grep emitted malformed non-JSON output: {str(jde)}",
                            status=ScannerStatus.ERROR,
                            repository_id=repository_id,
                            analysis_run_id=analysis_run_id,
                            commit_hash=commit_hash,
                        )
                    ]

                if isinstance(matches, dict):
                    matches = matches.get("results", []) or matches.get("matches", [])

                if not matches:
                    return [
                        CandidateFinding(
                            finding_id="ASTGREP-CLEAN",
                            tool="ast-grep",
                            tool_version=version_str,
                            check_id="astgrep.scan.clean",
                            file=repo_path,
                            message="ast-grep scan executed: 0 pattern violations detected.",
                            status=ScannerStatus.EXECUTED_NO_MATCH,
                            repository_id=repository_id,
                            analysis_run_id=analysis_run_id,
                            commit_hash=commit_hash,
                        )
                    ]

                findings = []
                for idx, m in enumerate(matches, 1):
                    findings.append(
                        CandidateFinding(
                            finding_id=f"ASTGREP-{idx:03d}",
                            tool="ast-grep",
                            tool_version=version_str,
                            check_id=m.get("rule_id", "astgrep.pattern"),
                            file=m.get("file", repo_path),
                            line=m.get("range", {}).get("start", {}).get("line"),
                            line_range=f"{m.get('range', {}).get('start', {}).get('line')}-{m.get('range', {}).get('end', {}).get('line')}",
                            message=m.get("message", "ast-grep structural pattern match"),
                            severity=str(m.get("severity", "MEDIUM")).upper(),
                            category="Structural Violation",
                            status=ScannerStatus.EXECUTED_MATCH,
                            repository_id=repository_id,
                            analysis_run_id=analysis_run_id,
                            commit_hash=commit_hash,
                            raw_payload=m,
                        )
                    )
                return findings

            return [
                CandidateFinding(
                    finding_id="ASTGREP-ERROR",
                    tool="ast-grep",
                    tool_version=version_str,
                    check_id="astgrep.execution.error",
                    file=repo_path,
                    message=f"ast-grep execution exited with code {proc.returncode}: {proc.stderr[:200]}",
                    status=ScannerStatus.ERROR,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        except subprocess.TimeoutExpired:
            return [
                CandidateFinding(
                    finding_id="ASTGREP-TIMEOUT",
                    tool="ast-grep",
                    tool_version=version_str,
                    check_id="astgrep.execution.timeout",
                    file=repo_path,
                    message=f"ast-grep execution timed out after {self.timeout_seconds}s.",
                    status=ScannerStatus.ERROR,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]
        except Exception as e:
            return [
                CandidateFinding(
                    finding_id="ASTGREP-EXCEPTION",
                    tool="ast-grep",
                    tool_version=version_str,
                    check_id="astgrep.execution.exception",
                    file=repo_path,
                    message=f"ast-grep scanner encountered exception: {str(e)}",
                    status=ScannerStatus.ERROR,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]
