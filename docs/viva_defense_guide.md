# DevLensX v1 — Viva & Technical Defense Guide

**Purpose:** Comprehensive reference for technical Q&A, viva defense, and architectural justification.

---

## 1. Core Architectural Q&A

### Q1: Why use AST parsing (`javalang`) instead of passing raw code directly to an LLM?
**Answer:** AST parsing provides deterministic syntactic accuracy. An LLM operates probabilistically and frequently hallucinates non-existent methods, wrong parameter types, or fake classes. AST parsing guarantees ground-truth symbol verification before LLM interpretation.

### Q2: Why use an embedded property graph database (KuzuDB)?
**Answer:** Software components naturally form a directed property graph (`Controller -> Service -> Repository`). KuzuDB is an embedded C++ graph database supporting native Cypher queries, enabling multi-hop dependency traversals (`MATCH (a:Class)-[:DEPENDS_ON*1..3]->(b:Class)`) without IPC latency or external database server overhead.

### Q3: Why combine KuzuDB graph indexing with FAISS vector embeddings?
**Answer:** Structural graph dependencies and semantic similarity solve two different problems:
- **KuzuDB:** Resolves exact caller-callee chains, interface implementations, and injection edges.
- **FAISS:** Resolves semantic query similarity (e.g. finding *"where is JWT token created?"* even if class is named `AuthUtil`).

### Q4: What is the role of `RepositoryBrain`?
**Answer:** `RepositoryBrain` acts as the single, versioned snapshot for an `analysis_run_id`. All 6 Workspaces (`Understand`, `Ask`, `Debug`, `Build`, `Review`, `Wiki`) consume this single brain snapshot, preventing redundant codebase re-parsing and eliminating cross-workspace contradictions.

### Q5: What is the Fail-Closed Critic Agent?
**Answer:** The Critic Agent is the grounding gatekeeper. It evaluates all AI-generated assertions against AST and graph evidence. If an AI claim fails empirical verification ($\text{Score} < 50\%$), it is rejected and marked 🔴 **`INSUFFICIENT EVIDENCE`**.

### Q6: Why use SQLite for application state alongside KuzuDB for graph structure?
**Answer:**
- **SQLite:** Manages relational user accounts, auth tokens, repository metadata, and workspace history.
- **KuzuDB:** Manages high-performance graph traversals over codebase AST nodes.

### Q7: Why not make DevLensX 100% autonomous or LLM-driven?
**Answer:** Codebase understanding requires strict evidence. Autonomous LLMs produce plausible prose but lack empirical guarantees. DevLensX enforces the invariant: *Facts come from repository evidence; AI interprets those facts; unverified suggestions remain explicitly unverified.*
