"""
DevLensX Rule Catalog
Grounded in engineering rules inspired by Alibaba OpenCodeReview (Apache-2.0).
Provides positive defect patterns and negative suppression constraints ("Do not report when...").
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class ReviewRule:
    """Specialized language or framework review rule specification."""
    id: str
    name: str
    language: str
    guidelines: List[str]
    negative_constraints: List[str]
    # Programmatic suppression rules for pre-verifier candidate filtering
    suppression_criteria: List[Dict[str, Any]] = field(default_factory=list)

    def render_prompt(self) -> str:
        """Render markdown guidelines and negative constraints for the LLM prompt."""
        lines = [f"### Rules for {self.name} ({self.language})"]
        lines.append("#### Focus Areas & Defect Patterns:")
        for g in self.guidelines:
            lines.append(f"- {g}")
        lines.append("#### DO NOT REPORT (False Positive Suppression):")
        for nc in self.negative_constraints:
            lines.append(f"- {nc}")
        return "\n".join(lines)


RULE_CATALOG: Dict[str, ReviewRule] = {
    "java": ReviewRule(
        id="java",
        name="Java & JVM Frameworks",
        language="Java",
        guidelines=[
            "Logic errors: boundary condition off-by-one errors, missing break in switch, inverted boolean checks.",
            "Null safety: NullPointerException risk on unvalidated method arguments, chain calls without null checks.",
            "Database & Performance: N+1 query loops, executing queries inside loops, missing pagination on bulk data.",
            "Thread Safety: Check-then-act race conditions on shared mutable state, non-atomic compound operations.",
            "Resource Management: Unclosed streams/sockets/connections not using try-with-resources.",
        ],
        negative_constraints=[
            "Do NOT report thread-safety issues for method-local variables; method-local state is strictly stack-confined and thread-safe.",
            "Do NOT report thread-safety issues in single-threaded contexts or stateless request-scoped components.",
            "Do NOT report thread-safety issues on immutable objects or read-only collections.",
            "Do NOT report NPE if the variable was already guarded by an explicit null check (e.g. if (x != null), Optional, or Objects.requireNonNull).",
            "Do NOT report SQL injection on static constant queries or parameterized PreparedStatements / JPA parameters (:param).",
            "Do NOT report missing @Valid or validation on static views or GET endpoints without request parameters.",
        ],
        suppression_criteria=[
            {
                "category": "Concurrency",
                "condition": "local_variable",
                "message": "Suppressed: Variable is a method-local stack variable; thread-safety claims are not applicable.",
            },
            {
                "category": "Security",
                "issue": "SQL_INJECTION",
                "condition": "parameterized_or_constant",
                "message": "Suppressed: Query is parameterized or statically constant.",
            },
            {
                "category": "Correctness",
                "issue": "NPE",
                "condition": "null_guarded",
                "message": "Suppressed: Symbol is guarded by an explicit null-check upstream.",
            },
        ],
    ),
    "python": ReviewRule(
        id="python",
        name="Python",
        language="Python",
        guidelines=[
            "Mutable default arguments: def func(x=[]) or def func(x={}) shares state across invocations.",
            "Boundary handling: indexing empty collections (xs[0]), missing key handling (dict[k] vs dict.get(k)).",
            "Floating point equality: using '==' to compare floats instead of math.isclose.",
            "Error handling: bare 'except:' catching SystemExit/KeyboardInterrupt, broad try blocks, swallowed exceptions with pass.",
            "Resource leaks: files/sockets opened without 'with' statement context managers.",
        ],
        negative_constraints=[
            "Do NOT report mutable defaults when the function never mutates the argument or uses it as a documented sentinel/cache.",
            "Do NOT report unused imports or unreferenced variables in .pyi stub files.",
            "Do NOT report missing key errors if the key existence was verified upstream with 'in'.",
            "Do NOT report resource leaks in short-lived scripts or when handled by framework lifecycles.",
            "Do NOT report '==' with None as a blocking defect; it is a style preference (is None preferred).",
        ],
        suppression_criteria=[
            {
                "category": "Correctness",
                "issue": "MUTABLE_DEFAULT",
                "condition": "unmutated_or_sentinel",
                "message": "Suppressed: Default argument is not mutated or acts as sentinel.",
            },
            {
                "category": "Correctness",
                "issue": "KEY_ERROR",
                "condition": "key_guarded",
                "message": "Suppressed: Key existence verified by upstream membership check.",
            },
        ],
    ),
    "typescript_javascript": ReviewRule(
        id="typescript_javascript",
        name="TypeScript & JavaScript",
        language="TypeScript/JavaScript",
        guidelines=[
            "Unhandled Promises: floating promises missing await or .catch(), unhandled rejection risks.",
            "React Hooks: useEffect / useMemo missing dependencies in dependency array, causing stale closures.",
            "Memory leaks: addEventListener without corresponding removeEventListener in unmount/cleanup.",
            "Type safety: unsafe 'as any' casts bypassing compile-time contract, unchecked optional properties.",
            "Loose equality: '==' coercion causing subtle falsy bugs (0 vs '' vs false); use '==='.",
        ],
        negative_constraints=[
            "Do NOT report floating promises when explicitly marked with 'void' or intended fire-and-forget with global error handler.",
            "Do NOT report missing optional checks when upstream optional chaining (?.), nullish coalescing (??), or type guards are present.",
            "Do NOT report useEffect dependency warnings for stable setter functions (like useState setState or useRef).",
            "Do NOT report type assertions in unit test fixture files.",
        ],
        suppression_criteria=[
            {
                "category": "Async",
                "issue": "FLOATING_PROMISE",
                "condition": "void_marked",
                "message": "Suppressed: Promise explicitly discarded via void.",
            },
            {
                "category": "React",
                "issue": "STALE_CLOSURE",
                "condition": "stable_setter",
                "message": "Suppressed: React dispatch/setter is guaranteed stable across renders.",
            },
        ],
    ),
    "go": ReviewRule(
        id="go",
        name="Go",
        language="Go",
        guidelines=[
            "Goroutine leaks: spawning goroutines blocked indefinitely on channels without cancel context or buffer.",
            "Error handling: ignoring returned error without checking 'err != nil'.",
            "Nil pointer dereference: accessing fields of returned pointers when err != nil before checking error.",
            "Defer in loops: deferring file/resource closure inside loops causing resource exhaustion before loop ends.",
        ],
        negative_constraints=[
            "Do NOT report ignored errors if explicitly assigned to blank identifier '_' with documented justification.",
            "Do NOT report goroutine leaks in main() package initialization or test helpers that exit immediately.",
            "Do NOT report defer inside loops if wrapped in an immediately-invoked anonymous function.",
        ],
        suppression_criteria=[
            {
                "category": "Concurrency",
                "issue": "GOROUTINE_LEAK",
                "condition": "scoped_or_test",
                "message": "Suppressed: Goroutine lifecycle is bounded by test or main shutdown.",
            },
        ],
    ),
    "rust": ReviewRule(
        id="rust",
        name="Rust",
        language="Rust",
        guidelines=[
            "Unsafe blocks: raw pointer dereferencing without invariant verification, mutable aliasing, unaligned memory reads.",
            "Panics in production paths: calling .unwrap() or .expect() on user input, request handlers, or network I/O.",
            "Lifetime and borrow hazards: holding RefCell borrows across yield points in async code.",
            "Resource leaks: mem::forget on resources requiring drop cleanup.",
        ],
        negative_constraints=[
            "Do NOT report .unwrap() or .expect() in unit test functions (#[test]) or test modules (#[cfg(test)]).",
            "Do NOT report unsafe blocks inside standard library wrappers or when preceded by explicit safety invariants comment (// SAFETY:).",
            "Do NOT report panics in build scripts (build.rs) or CLI entry points where fast-fail is intended.",
        ],
        suppression_criteria=[
            {
                "category": "Reliability",
                "issue": "UNWRAP_PANIC",
                "condition": "test_module",
                "message": "Suppressed: .unwrap() is acceptable in unit tests and test modules.",
            },
        ],
    ),
    "cpp": ReviewRule(
        id="cpp",
        name="C & C++",
        language="C/C++",
        guidelines=[
            "Memory corruption: buffer overflow, array index out of bounds, off-by-one in memcpy/memmove/strncpy.",
            "Use-After-Free: accessing pointers after free() or delete, dangling references to temporary or stack objects.",
            "Memory leaks: raw pointers allocated with new/malloc without corresponding delete/free on all exit paths.",
            "Polymorphism hazards: base class with virtual methods lacking a virtual destructor.",
            "Undefined behavior: uninitialized variables, integer overflow in signed arithmetic.",
        ],
        negative_constraints=[
            "Do NOT report memory leaks when resources are managed by RAII smart pointers (std::unique_ptr, std::shared_ptr).",
            "Do NOT report buffer overflows when bounds are guaranteed by std::span, std::array, or std::vector.",
            "Do NOT report uninitialized variables if assigned via reference output parameters in standard APIs.",
        ],
        suppression_criteria=[
            {
                "category": "Memory",
                "issue": "MEMORY_LEAK",
                "condition": "smart_pointer_or_raii",
                "message": "Suppressed: Resource managed by RAII / smart pointer container.",
            },
        ],
    ),
    "kotlin": ReviewRule(
        id="kotlin",
        name="Kotlin & Coroutines",
        language="Kotlin",
        guidelines=[
            "Coroutine scope hazards: GlobalScope.launch causing background coroutine leaks, unhandled exceptions cancelling parent scopes.",
            "Null safety bypass: excessive double-bang (!!) operator risking KotlinNullPointerException.",
            "Blocking calls in coroutines: Thread.sleep() or blocking I/O on Dispatchers.Main or Dispatchers.Default without Dispatchers.IO.",
            "StateFlow / SharedFlow: emitting from multiple threads without thread-safe synchronization.",
        ],
        negative_constraints=[
            "Do NOT report (!!) operator when immediately preceded by an explicit smart-cast or null-check contract.",
            "Do NOT report blocking calls if wrapped in withContext(Dispatchers.IO).",
            "Do NOT report coroutine scope leaks for viewModelScope or lifecycleScope tied to Android/KMP lifecycles.",
        ],
        suppression_criteria=[
            {
                "category": "Concurrency",
                "issue": "COROUTINE_BLOCKING",
                "condition": "io_dispatcher",
                "message": "Suppressed: Blocking operation safely dispatched on Dispatchers.IO.",
            },
        ],
    ),
    "swift": ReviewRule(
        id="swift",
        name="Swift & Concurrency",
        language="Swift",
        guidelines=[
            "Retain cycles: strong reference cycles in escaping closures capturing self without [weak self] or [unowned self].",
            "Force unwrap: force unwrap (!) or force try (try!) in production runtime paths.",
            "Actor isolation: mutable state access crossing actor boundaries without await.",
        ],
        negative_constraints=[
            "Do NOT report retain cycles in non-escaping closures (like standard Array.map or filter).",
            "Do NOT report force unwrap in IBOutlet properties initialized by storyboards/xibs or test suites.",
        ],
        suppression_criteria=[
            {
                "category": "Memory",
                "issue": "RETAIN_CYCLE",
                "condition": "non_escaping",
                "message": "Suppressed: Non-escaping closure cannot retain self past execution.",
            },
        ],
    ),
    "sql": ReviewRule(
        id="sql",
        name="SQL & Database Migrations",
        language="SQL",
        guidelines=[
            "Schema migration hazards: adding NOT NULL column without DEFAULT on large tables causing table lock.",
            "Index efficiency: missing indexes on foreign keys and frequently filtered columns.",
            "Dynamic SQL: string concatenation in stored procedures causing SQL injection vulnerabilities.",
        ],
        negative_constraints=[
            "Do NOT report table locks on new empty tables created in the same migration file.",
            "Do NOT report SQL injection on internal metadata queries with constant table names.",
        ],
        suppression_criteria=[
            {
                "category": "Database",
                "issue": "TABLE_LOCK",
                "condition": "new_table",
                "message": "Suppressed: DDL operates on newly created table with zero rows.",
            },
        ],
    ),
    "dockerfile": ReviewRule(
        id="dockerfile",
        name="Dockerfile & Container Security",
        language="Dockerfile",
        guidelines=[
            "Least privilege: running container processes as default root user instead of dedicated non-root USER.",
            "Image bloat: missing apt-get clean or rm -rf /var/lib/apt/lists/* in RUN instructions.",
            "Image tag pinning: using ':latest' tag for base images causing non-deterministic builds.",
            "Secret leakage: COPY or ADD of sensitive files (.env, id_rsa, credentials) into image layers.",
        ],
        negative_constraints=[
            "Do NOT report root user warning if a downstream USER directive switches to non-root before ENTRYPOINT.",
            "Do NOT report image tag pinning for scratch or official base images with explicit digest hashes (@sha256:...).",
            "Do NOT report secret leakage if the file is explicitly listed in .dockerignore.",
        ],
        suppression_criteria=[
            {
                "category": "Security",
                "issue": "ROOT_USER",
                "condition": "non_root_switched",
                "message": "Suppressed: Dockerfile contains downstream USER instruction before runtime entrypoint.",
            },
        ],
    ),
    "ci_cd": ReviewRule(
        id="ci_cd",
        name="CI/CD & GitHub Actions",
        language="YAML / Workflows",
        guidelines=[
            "Action pinning: using mutable branch refs (@master, @main) instead of immutable commit SHAs for third-party actions.",
            "Script injection: interpolating untrusted context expressions (${{ github.event.issue.title }}) directly in run scripts.",
            "Secret leakage: printing secrets or unmasked environment variables in log output.",
        ],
        negative_constraints=[
            "Do NOT report action pinning for first-party actions from actions/* (e.g. actions/checkout@v4).",
            "Do NOT report script injection if the untrusted context expression is passed via an environment variable.",
        ],
        suppression_criteria=[
            {
                "category": "Security",
                "issue": "SCRIPT_INJECTION",
                "condition": "env_var_isolated",
                "message": "Suppressed: Context expression is passed safely via intermediate environment variable.",
            },
        ],
    ),
    "xml_build": ReviewRule(
        id="xml_build",
        name="Build & Dependency Manifests",
        language="XML / Build Configuration",
        guidelines=[
            "Dependency conflicts: duplicate artifact definitions with divergent version tags.",
            "Security: hardcoded API keys, passwords, or tokens in build scripts or properties files.",
            "SQL XML Mapping: SQL injection in MyBatis XML mappers using raw ${param} interpolation instead of #{param}.",
        ],
        negative_constraints=[
            "Do NOT report ${param} in MyBatis XML if used strictly for trusted table/column names that cannot accept bind parameters.",
            "Do NOT report environment variable placeholders (e.g. ${env.DB_PASS}) as hardcoded secrets.",
            "Do NOT report dependency version overrides intentionally configured in dependencyManagement.",
        ],
        suppression_criteria=[
            {
                "category": "Security",
                "issue": "HARDCODED_SECRET",
                "condition": "env_placeholder",
                "message": "Suppressed: Secret uses environment variable interpolation.",
            },
        ],
    ),
}


def get_rule_by_id(rule_id: str) -> Optional[ReviewRule]:
    """Retrieve rule definition by id."""
    return RULE_CATALOG.get(rule_id)
