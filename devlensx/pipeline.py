"""
DevLensX Pipeline Facade.
Provides Pipeline.analyze entrypoint for repository intelligence analysis.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


class Pipeline:
    @staticmethod
    def analyze(repo_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run repository intelligence analysis on a target path.
        """
        from devlensx.api.main import AnalyzeRequest, analyze_repository
        req = AnalyzeRequest(repo_path=str(repo_path))
        return analyze_repository(req)
