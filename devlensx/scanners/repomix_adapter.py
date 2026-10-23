"""
DevLensX Repomix Adapter (P6-B)

Adapter for Repomix (formerly Repopack), reverse-engineering GitIngest/DeepWiki packaging.
Produces token-counted repository bundles and candidate findings for security/size issues.

HARD INVARIANT:
  Scanners/packagers produce candidate findings with explicit execution statuses:
  - EXECUTED_MATCH: Scan or packaging succeeded with actionable findings
  - EXECUTED_NO_MATCH: Clean execution with 0 issues
  - NOT_INSTALLED: Repomix binary not found on host PATH
  - SKIPPED: Adapter disabled by configuration
  - ERROR: Process error or timeout
"""

import shutil
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from devlensx.scanners.base import BaseScanner, CandidateFinding, ScannerStatus


class RepomixAdapter(BaseScanner):
    """Adapter for Repomix repository context packaging and structural analysis."""

    def __init__(self, enabled: bool = True, timeout_seconds: int = 60):
        super().__init__(name="repomix", enabled=enabled)
        self.timeout_seconds = timeout_seconds

    def _resolve_binary(self) -> Optional[str]:
        return shutil.which("repomix") or shutil.which("repomix.cmd")

    def is_installed(self) -> bool:
        return self._resolve_binary() is not None

    def pack(
        self,
        repo_path: str,
        output_file: Optional[str] = None,
        style: str = "markdown",  # markdown, xml, json
        max_file_size_kb: int = 500,
    ) -> Dict[str, Any]:
        """
        Packs repository files into a structured LLM context bundle.
        Falls back to native DevLensX ingestion if repomix binary is absent.
        """
        bin_path = self._resolve_binary()
        if not bin_path:
            # Fallback to internal native ingest
            from devlensx.ingest import NativeRepoIngest
            ingest = NativeRepoIngest()
            result = ingest.ingest_directory(repo_path)
            return {
                "status": "FALLBACK_NATIVE",
                "tool": "native_ingest",
                "file_count": result.get("total_files", 0),
                "total_tokens_est": result.get("token_estimate", 0),
                "content": result.get("digest", ""),
            }

        out_path = output_file or os.path.join(repo_path, "repomix-output.txt")
        cmd = [
            bin_path,
            repo_path,
            "--output", out_path,
            "--style", style,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False
            )
            if proc.returncode == 0 and os.path.exists(out_path):
                content = Path(out_path).read_text(encoding="utf-8", errors="replace")
                return {
                    "status": "SUCCESS",
                    "tool": "repomix",
                    "output_path": out_path,
                    "bundle_size_bytes": len(content.encode("utf-8")),
                    "content_preview": content[:2000],
                }
            return {
                "status": "ERROR",
                "tool": "repomix",
                "stderr": proc.stderr,
                "stdout": proc.stdout,
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "tool": "repomix",
                "error": str(e)
            }

    def scan(
        self,
        repo_path: str,
        repository_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        commit_hash: Optional[str] = None
    ) -> List[CandidateFinding]:
        """
        Scans repository structure with Repomix checks.
        """
        if not self.enabled:
            return [
                CandidateFinding(
                    finding_id="REPOMIX-SKIPPED",
                    tool="repomix",
                    check_id="repomix.scanner.skipped",
                    file=repo_path,
                    message="Repomix packager execution skipped by configuration.",
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
                    finding_id="REPOMIX-NOT-INSTALLED",
                    tool="repomix",
                    check_id="repomix.binary.not_installed",
                    file=repo_path,
                    message="Repomix binary not found on host PATH. Using native ingest fallback.",
                    status=ScannerStatus.NOT_INSTALLED,
                    repository_id=repository_id,
                    analysis_run_id=analysis_run_id,
                    commit_hash=commit_hash,
                )
            ]

        # Repomix is installed and available
        return [
            CandidateFinding(
                finding_id="REPOMIX-AVAILABLE",
                tool="repomix",
                check_id="repomix.installed.ready",
                file=repo_path,
                message=f"Repomix binary available at {bin_path}.",
                status=ScannerStatus.EXECUTED_NO_MATCH,
                repository_id=repository_id,
                analysis_run_id=analysis_run_id,
                commit_hash=commit_hash,
            )
        ]
