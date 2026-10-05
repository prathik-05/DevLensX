"""
DevLensX Rule Sniffer & Negative Constraint Evaluator
Path-based rule sniffing and false-positive suppression inspired by Alibaba OpenCodeReview (Apache-2.0).
"""

from __future__ import annotations
import fnmatch
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from devlensx.review.rules.rule_catalog import RULE_CATALOG, ReviewRule


# Mapping glob patterns to rule IDs (similar to OCR system_rules.json)
PATH_RULE_MAPPINGS: List[Tuple[str, str]] = [
    ("*.java", "java"),
    ("*.py", "python"),
    ("*.pyi", "python"),
    ("*.ts", "typescript_javascript"),
    ("*.tsx", "typescript_javascript"),
    ("*.js", "typescript_javascript"),
    ("*.jsx", "typescript_javascript"),
    ("*.mjs", "typescript_javascript"),
    ("*.cjs", "typescript_javascript"),
    ("*.go", "go"),
    ("*.rs", "rust"),
    ("*.c", "cpp"),
    ("*.cpp", "cpp"),
    ("*.cc", "cpp"),
    ("*.cxx", "cpp"),
    ("*.h", "cpp"),
    ("*.hpp", "cpp"),
    ("*.kt", "kotlin"),
    ("*.kts", "kotlin"),
    ("*.swift", "swift"),
    ("*.sql", "sql"),
    ("Dockerfile*", "dockerfile"),
    ("*.dockerfile", "dockerfile"),
    (".github/workflows/*.yml", "ci_cd"),
    (".github/workflows/*.yaml", "ci_cd"),
    ("*workflow*.yml", "ci_cd"),
    ("*workflow*.yaml", "ci_cd"),
    ("pom.xml", "xml_build"),
    ("*mapper*.xml", "xml_build"),
    ("*dao*.xml", "xml_build"),
    ("build.gradle*", "xml_build"),
    ("package.json", "xml_build"),
]


class RuleSniffer:
    """Sniffs changed paths from diff or file lists and compiles matched review rules."""

    @staticmethod
    def extract_paths_from_diff(diff: str) -> List[str]:
        """Extract changed file paths from a unified git diff."""
        paths: Set[str] = set()
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                p = line[6:].strip()
                if p and p != "/dev/null":
                    paths.add(p)
            elif line.startswith("--- a/"):
                p = line[6:].strip()
                if p and p != "/dev/null":
                    paths.add(p)
        return sorted(list(paths))

    @classmethod
    def match_rule_ids_for_path(cls, file_path: str) -> List[str]:
        """Find matching rule catalog IDs for a given file path."""
        p_clean = file_path.replace("\\", "/").lower()
        matched: List[str] = []
        for pattern, rule_id in PATH_RULE_MAPPINGS:
            # Check filename or full path match
            basename = p_clean.split("/")[-1]
            if fnmatch.fnmatch(basename, pattern.lower()) or fnmatch.fnmatch(p_clean, f"*/{pattern.lower()}"):
                if rule_id not in matched:
                    matched.append(rule_id)
        return matched

    @classmethod
    def sniff(cls, input_data: str | List[str]) -> List[ReviewRule]:
        """Given a diff string or list of file paths, return list of relevant ReviewRules."""
        if isinstance(input_data, str):
            paths = cls.extract_paths_from_diff(input_data)
        else:
            paths = input_data

        matched_rule_ids: Set[str] = set()
        for path in paths:
            for rid in cls.match_rule_ids_for_path(path):
                matched_rule_ids.add(rid)

        rules: List[ReviewRule] = []
        for rid in sorted(list(matched_rule_ids)):
            rule = RULE_CATALOG.get(rid)
            if rule:
                rules.append(rule)
        return rules

    @classmethod
    def render_prompt_for_diff(cls, diff: str) -> str:
        """Render markdown prompt block for all rules matching files in the diff."""
        rules = cls.sniff(diff)
        if not rules:
            return ""
        blocks = ["## Specialized Code Review Constraints & Guidelines:"]
        for rule in rules:
            blocks.append(rule.render_prompt())
        return "\n\n".join(blocks)


def evaluate_negative_constraints(
    finding: Dict[str, Any],
    code_context: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates candidate findings against negative review constraints.
    Returns:
        (True, reason) -> Suppress candidate finding (false positive).
        (False, None)  -> Candidate is valid and should proceed to ClaimVerifier.
    """
    category = str(finding.get("category", "")).lower()
    title = str(finding.get("title", "")).lower()
    explanation = str(finding.get("explanation", "")).lower()
    combined_text = f"{title} {explanation} {finding.get('description', '')}".lower()
    ctx = (code_context or "").lower()

    # Rule 1: Concurrency / Thread Safety on Local Variables
    if "concurren" in category or "thread" in category or "race condition" in combined_text or "thread safe" in combined_text:
        # Check if finding mentions local variable or context indicates stack confinement
        if "local variable" in combined_text or "local var" in combined_text:
            return True, "Suppressed by negative constraint: method-local variable is stack-confined and inherently thread-safe."
        if ctx and ("// local" in ctx or "final var " in ctx or "int " in ctx and "private " not in ctx):
            if "escape" not in combined_text and "shared" not in combined_text:
                return True, "Suppressed by negative constraint: no evidence that local state escapes the method."

    # Rule 2: SQL Injection on Constant Strings or Parameterized Queries
    if "sql" in combined_text and ("injection" in combined_text or "concatenat" in combined_text):
        if "preparedstatement" in ctx or "@param" in ctx or ":param" in ctx or "?" in ctx:
            if "dynamic" not in combined_text:
                return True, "Suppressed by negative constraint: query uses parameterized binding."
        # If the query string has no dynamic variable concatenation (just literal string)
        if re.search(r'select\s+.*\s+from\s+[\w_]+(?:\s+where\s+[\w_]+\s*=\s*\?)', ctx):
            return True, "Suppressed by negative constraint: query is statically parameterized."

    # Rule 3: Null Safety / NPE where variable is already null-checked upstream
    if "npe" in combined_text or "nullpointer" in combined_text or "null safety" in combined_text:
        if "!= null" in ctx or "objects.requirenonnull" in ctx or "optional.ofnullable" in ctx:
            return True, "Suppressed by negative constraint: symbol is guarded by explicit null check."

    # Rule 4: Floating Promise where void operator is explicitly applied
    if "floating promise" in combined_text or "unhandled promise" in combined_text:
        if "void " in ctx:
            return True, "Suppressed by negative constraint: promise explicitly discarded with void."

    # Rule 5: Environment variable placeholders reported as hardcoded secrets
    if "secret" in combined_text or "credential" in combined_text or "token" in combined_text:
        if re.search(r'\$\{(?:env\.)?[a-zA-Z0-9_]+\}', ctx) or "system.getenv" in ctx or "process.env" in ctx:
            return True, "Suppressed by negative constraint: placeholder references environment variable, not hardcoded secret."

    # Rule 6: Rust unwrap() / expect() in tests
    if "unwrap" in combined_text or "expect" in combined_text:
        if "#[test]" in ctx or "#[cfg(test)]" in ctx or "mod test" in ctx or "test_" in finding.get("file_path", ""):
            return True, "Suppressed by negative constraint: unwrap()/expect() is legitimate in test functions and modules."

    # Rule 7: C/C++ memory leak on RAII smart pointers
    if "leak" in combined_text or "use-after-free" in combined_text:
        if "unique_ptr" in ctx or "shared_ptr" in ctx or "make_unique" in ctx or "make_shared" in ctx:
            return True, "Suppressed by negative constraint: resource is managed by RAII smart pointer."

    # Rule 8: Dockerfile root user warning when downstream USER directive exists
    if "root user" in combined_text or "user root" in combined_text:
        if "user " in ctx and "user root" not in ctx:
            return True, "Suppressed by negative constraint: Dockerfile specifies non-root USER instruction."

    # Rule 9: CI/CD script injection when context expression passed via env var
    if "script injection" in combined_text or "expression injection" in combined_text:
        if "env:" in ctx and "${{" in ctx:
            return True, "Suppressed by negative constraint: context expression is safely isolated in env block."

    return False, None
