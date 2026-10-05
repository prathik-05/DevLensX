"""
DevLensX Module 5: Security Agent

Scans repository AST output and source code for:
  - Hardcoded secrets and password variables (field-name heuristics).
  - Insecure REST endpoints lacking authorization annotations
    (class- and method-level annotations checked).
  - Cross-checks findings against Semgrep static analysis output.
"""

import re
import subprocess
import json
import shutil
import os

_SEMGREP_CONFIG_MAP = {
    "java": "p/java",
    "python": "p/python",
    "javascript": "p/javascript",
    "typescript": "p/javascript",
}

_SOURCE_EXTENSIONS = {".java", ".py", ".js", ".ts", ".go", ".cs"}

class SecurityAgent:
    def __init__(self, semgrep_enabled=True):
        self.semgrep_enabled = semgrep_enabled

    def scan_semgrep(self, repo_path, language=None):
        """Runs Semgrep static analyzer if available as ground truth."""
        if not self.semgrep_enabled or not shutil.which("semgrep"):
            return []
        try:
            config = _SEMGREP_CONFIG_MAP.get(language, "p/default")
            cmd = ["semgrep", f"--config={config}", "--json", repo_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                results = []
                for item in data.get("results", []):
                    results.append({
                        "check_id": item.get("check_id"),
                        "file": item.get("path"),
                        "line": item.get("start", {}).get("line"),
                        "message": item.get("extra", {}).get("message")
                    })
                return results
        except Exception:
            pass
        return []

    def analyze(self, repo_model, repo_path=".", language=None):
        """Analyzes Security risks via AST rules & Semgrep integration."""
        findings = []

        # 1. Hardcoded Secret & Weak Password detection in fields
        secret_pattern = re.compile(r"(password|secret|apikey|api_key|token|private_key)", re.IGNORECASE)
        for c in repo_model.get("classes", []):
            if not isinstance(c, dict):
                continue
            for f in c.get("fields", []) or []:
                if not isinstance(f, dict):
                    continue
                fname = str(f.get("name", ""))
                if fname and secret_pattern.search(fname):
                    findings.append({
                        "agent": "SecurityAgent",
                        "category": "Hardcoded Secret",
                        "title": f"Potential Hardcoded Secret Field: '{fname}' in {c.get('name', '')}",
                        "severity": "HIGH",
                        "class_name": c.get("name", ""),
                        "file": c.get("file", ""),
                        "claim": f"Class {c.get('name', '')} contains field '{fname}' which matches secret naming patterns.",
                        "evidence": {
                            "field_name": fname,
                            "field_type": f.get("type", "")
                        }
                    })

        # 2. Insecure REST Endpoints (lack of Security annotations).
        # Endpoints may live inline on the class (legacy schema) or at model
        # level matched by handler/file (URM schema) — support both.
        try:
            from devlensx.deep_reasoning import build_method_index, prod_methods, handler_matches
            _method_index = build_method_index(repo_model.get("classes", []))
        except Exception:
            _method_index = {}
        _model_endpoints = [e for e in (repo_model.get("endpoints", []) or []) if isinstance(e, dict)]
        _CONTROLLER_STEREOTYPES = {
            "Controller", "RestController", "Router", "APIRouter", "Endpoint", "Handler", "Route"
        }
        for c in repo_model.get("classes", []):
            if not isinstance(c, dict):
                continue
            st = c.get("stereotype") or ""
            is_ctrl = st in _CONTROLLER_STEREOTYPES or "controller" in str(c.get("name", "")).lower()
            inline_eps = [e for e in (c.get("endpoints", []) or []) if isinstance(e, dict)]
            model_eps = [e for e in _model_endpoints
                         if handler_matches(str(e.get("handler", "")), str(c.get("name", "")))]
            if not is_ctrl and not inline_eps and not model_eps:
                continue
            if not inline_eps and not model_eps:
                continue
            anns = [str(a).lower() for a in (c.get("annotations", []) or [])]
            for m in prod_methods(_method_index, str(c.get("name", ""))):
                anns.extend(str(a).lower() for a in (m.get("annotations", []) or []))
            if any("secur" in a or "auth" in a or "preauthorize" in a or "guard" in a for a in anns):
                continue
            for ep in (inline_eps + model_eps):
                http_verb = ep.get("http_annotation") or ep.get("http_method") or ep.get("method", "GET")
                route = ep.get("route") or ep.get("path") or ep.get("full_path", "/")
                findings.append({
                    "agent": "SecurityAgent",
                    "category": "API Security",
                    "title": f"Unprotected REST Endpoint: {http_verb} {route}",
                    "severity": "MEDIUM",
                    "class_name": c.get("name", ""),
                    "file": c.get("file", ""),
                    "claim": f"Endpoint {route} in handler {c.get('name', '')} does not specify explicit authentication guards or authorization annotations/middleware.",
                    "evidence": {
                        "endpoint": f"{http_verb} {route}",
                        "controller": c.get("name", "")
                    }
                })

        # 3. Cross-check against Semgrep ground truth
        semgrep_results = self.scan_semgrep(repo_path, language=language)
        for s in semgrep_results:
            findings.append({
                "agent": "SecurityAgent",
                "category": "Semgrep Violation",
                "title": f"Static Analysis Violation: {s['check_id']}",
                "severity": "HIGH",
                "class_name": os.path.splitext(os.path.basename(s["file"]))[0],
                "file": s["file"],
                "claim": f"Semgrep static analyzer confirmed rule violation {s['check_id']} at line {s['line']}.",
                "evidence": s
            })

        return {
            "semgrep_count": len(semgrep_results),
            "findings": findings
        }
