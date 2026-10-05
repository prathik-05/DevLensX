# DevLensX — Complete Codebase Architecture & System Reference

> **Product:** DevLensX — Evidence-Verified Software Engineering Intelligence Platform  
> **Status:** Production-Ready · Python 3.13 / FastAPI / KùzuDB / Tree-sitter / React 19 / TypeScript / Vite / Tailwind v4  
> **Date:** October 2026  
> **Repository Root:** `d:\projects\DevLensX` (Primary) · `C:\Users\SVCS\Desktop\DevLensX` (Sync Replica)

---

## 1. Directory Tree & High-Level Layout

```text
DevLensX/
├── devlensx/                       # Core Python Backend Package
│   ├── agents/                     # Multi-Agent Specialist Analyzers
│   │   ├── architecture_agent.py   # God-class & coupling detector
│   │   ├── security_agent.py       # Vulnerability & auth bypass sniffer
│   │   ├── change_impact_agent.py  # Blast-radius cascade tracker
│   │   └── reviewer_agent.py       # Code review synthesis agent
│   ├── api/                        # FastAPI REST API Layer
│   │   ├── main.py                 # Core application entrypoint & state
│   │   └── routes/                 # Modular API Route Controllers
│   │       ├── auth.py             # User authentication & token management
│   │       ├── repositories.py     # Repository CRUD & filesystem registry
│   │       ├── copilot.py          # Grounded AI assistant chat
│   │       ├── debug.py            # Stack trace AST & Graph debugger
│   │       ├── git.py              # Git branch, commit, and diff tracker
│   │       ├── wiki.py             # DeepWiki hierarchical doc generator
│   │       ├── evidence.py         # Evidence inspection & audit ledger
│   │       ├── diagrams.py         # C4 & Mermaid dynamic visualizer
│   │       ├── chat.py             # Contextual repo chat streams
│   │       ├── workspace.py        # Snapshot coordinator & multi-repo sync
│   │       ├── incremental.py      # Git diff AST change analyzer
│   │       ├── codemap.py          # Interactive architectural tour API
│   │       ├── codereview.py       # Code Turtle PR review & diff repair
│   │       ├── evaluation.py       # Ground-truth benchmarks & metrics
│   │       ├── governance.py       # Architectural rules & contract checks
│   │       ├── digest.py           # Legacy GitIngest bridge
│   │       └── ingest_routes.py    # Native Repo Ingest & analyze-from-ingest
│   ├── core/                       # Core Security & Configuration
│   │   └── security.py             # Path-traversal & SSRF guards
│   ├── critic/                     # Deterministic Ground-Truth Gate
│   │   ├── claim_verifier.py       # Atomic claim (s,p,o) verification gate
│   │   └── evidence_resolver.py    # Source byte-span & hash validator
│   ├── db/                         # Relational Storage & SQLAlchemy Models
│   │   ├── database.py             # Sessionmaker & DB engine
│   │   └── models.py               # Repository, Finding, User tables
│   ├── governance/                 # Architectural Governance Engine
│   │   ├── engine.py               # Declarative policy evaluator
│   │   ├── rules.py                # ARCH-001 to ARCH-004 catalog
│   │   ├── cycles.py               # Johnson's cycle classification algorithm
│   │   └── contracts.py            # Producer-Consumer API contract checker
│   ├── graph/                      # Kùzu Embedded Property Graph
│   │   ├── db.py                   # Columnar Cypher database driver
│   │   ├── schema.py               # Class, Method, Endpoint node & edge schemas
│   │   └── queries.py              # Multi-hop neighborhood traversal Cypher queries
│   ├── ingest.py                   # Native GitIngest context bundler & engine
│   ├── pipeline.py                 # Pipeline.analyze() execution facade
│   ├── repository.py               # Repository filtering & vendored skipping
│   ├── retrieval/                  # Hybrid GraphRAG Retrieval Plane
│   │   ├── vector_store.py         # FAISS dense embeddings index
│   │   └── graph_rag.py            # Vector-directed graph neighborhood expansion
│   ├── schemas/                    # Pydantic v2 Request & Response Models
│   │   ├── repository.py           # Analysis & repo schemas
│   │   ├── governance.py           # Rule & contract DTOs
│   │   └── auth.py                 # Identity & token schemas
│   ├── shared/                     # Cross-Cutting Primitives
│   │   └── types.py                # Language detection & common types
│   ├── understanding/              # Cognitive Reasoning & Knowledge Profiling
│   │   ├── capability_detector.py  # High-level domain capability detector
│   │   ├── flow_detector.py        # Controller -> Service -> Repo flow tracer
│   │   └── repository_profiler.py  # Codebase complexity & metric profiler
│   └── urm/                        # Universal Repository Model (Tree-sitter)
│       ├── models.py               # Language-neutral structural entities
│       └── adapters/               # 21-Language Tree-sitter parsers
│           ├── java_adapter.py     # Java syntax & annotation extractor
│           ├── python_adapter.py   # Python AST & decorator extractor
│           ├── typescript_adapter.py # TS/JS syntax & route extractor
│           └── go_adapter.py       # Go struct, interface & package extractor
├── web/                            # Modern React 19 Frontend Application
│   ├── src/
│   │   ├── App.tsx                 # Router, layout shell, & navigation
│   │   ├── apiClient.ts            # Typed REST API client & error handler
│   │   ├── store.ts                # Zustand global state container
│   │   ├── pages/
│   │   │   └── registry.ts         # Central view registry & command palette items
│   │   └── components/             # Dark-Glass UI Kit & Feature Views
│   │       ├── OverviewView.tsx    # Repo health, metrics & intelligence score
│   │       ├── IngestView.tsx      # Native GitIngest context bundler & tree
│   │       ├── WikiView.tsx        # DeepWiki architectural documentation
│   │       ├── CodemapView.tsx     # Blast-radius ranking & interactive tour
│   │       ├── ExplorerView.tsx    # Symbol browser & call graph explorer
│   │       ├── ArchitectureView.tsx# System dependency & layer graph viewer
│   │       ├── GovernanceView.tsx  # Architectural rules & contract inspector
│   │       ├── AIAssistantView.tsx # Conversational copilot with evidence
│   │       ├── CodeTurtleView.tsx  # Senior PR code review & diff patcher
│   │       ├── ReviewsView.tsx     # Security findings & engineering audit
│   │       ├── ChangeImpactView.tsx# 4-tier blast-radius cascade planner
│   │       ├── DebugView.tsx       # AST/Graph ground-truth stack trace debugger
│   │       ├── EvaluationView.tsx  # Golden benchmarks & precision metrics
│   │       ├── SettingsView.tsx    # API keys, providers & config options
│   │       ├── CommandPalette.tsx  # Spotlight Ctrl+K search & action drawer
│   │       ├── Header.tsx          # Top bar, status, search & theme toggle
│   │       ├── Sidebar.tsx         # Collapsible grouped navigation panel
│   │       └── GlassPanel.tsx      # Dark-glass visual container primitive
│   ├── package.json                # React 19, Vite, Lucide, Tailwind v4, Zustand
│   └── vite.config.ts              # Vite bundle configuration
├── tests/                          # Automated Pytest Suite
│   ├── test_native_ingest.py       # 14 tests: SSRF, globs, caps, format, tokens
│   ├── test_p5a_governance_rules.py# Governance rules: layer bypass, cycle, auth
│   ├── test_p5b_contracts.py       # Cross-service API producer/consumer contracts
│   ├── test_p5c_delivery_mcp_api.py# API endpoints & MCP protocol verification
│   ├── test_gitingest_wiki.py      # GitIngest integration & snapshot tests
│   └── ...                         # 47+ existing regression and unit tests
├── architecture.md                 # System architecture & module definitions
├── research_paper_framework.md     # Thesis & academic paper framework
├── pytest.ini                      # Pytest runner configuration
└── run_devlensx.py                 # Unified CLI: api, scan, ingest, eval
```

---

## 2. Core Architectural Pillars

### Pillar I: Deterministic Ingestion Plane (Tree-sitter & URM)
- Converts source files across 21 languages into a language-neutral **Universal Repository Model (URM)**.
- Structural entities:
  - `UrmClass` / `UrmInterface`: Name, package/namespace, stereotype, docstrings.
  - `UrmMethod` / `UrmFunction`: Signatures, return types, parameters, visibility, decorators.
  - `UrmDependency`: Imports, package includes, external vs. internal categorization.
  - `UrmCall`: Call-site AST resolution linking callers to callee targets.
  - `UrmEndpoint`: REST/RPC routes, HTTP methods, path params, query schemas, and security decorators (`@PreAuthorize`, `@RolesAllowed`).

### Pillar II: Dual Storage Substrate (Kùzu Property Graph + FAISS)
- **Kùzu Embedded Columnar Property Graph**: In-process Cypher execution with sub-millisecond edge traversals. Nodes: `Class`, `Method`, `Endpoint`, `Package`. Edges: `CALLS`, `EXTENDS`, `IMPLEMENTS`, `DEPENDS_ON`, `ROUTES_TO`.
- **FAISS Dense Vector Index**: Embeds docstrings, signatures, and implementation blocks using lightweight semantic embeddings for open-vocabulary entry points.
- **Evidence Reference Store**: Resolves every node/edge to a deterministic 6-tuple:
  $$\text{EvidenceRef} = (S, \text{filePath}, \text{lineStart}, \text{lineEnd}, \text{byteSpan}, \text{contentHash})$$

### Pillar III: Dual-Retrieval GraphRAG
- For developer queries, natural language questions, or diffs:
  1. FAISS identifies semantic entry-point symbols.
  2. Kùzu expands multi-hop topological neighborhoods (callers, callees, implementations, hierarchy).
  3. Context window receives structurally bounded subgraphs with verified source citations.

### Pillar IV: Deterministic ClaimVerifier Boundary
- Treats LLM output as unverified candidate claims:
  $$\text{Claim} = (\text{subject}, \text{predicate}, \text{object})$$
- Evaluates claims against 4 independent structural sources:
  1. **Graph Check:** Verifies node presence and edge relationship in Kùzu.
  2. **AST Check:** Verifies exact field names, parameter types, or annotation presence.
  3. **Structure Check:** Verifies file path existence and byte span hash on disk.
  4. **Semgrep Check:** Validates security rule AST patterns.
- Verdicts:
  - `🟢 VERIFIED`: Proven by repository evidence ($X/4 \ge 50\%$).
  - `🔵 AI_SUGGESTION`: Plausible heuristic reasoning beyond syntax.
  - `🔴 INSUFFICIENT_EVIDENCE`: Unproven, contradictory, or fabricated. Fails closed.

### Pillar V: Architectural Governance & Contract Verification
- **Rules (`devlensx/governance/`)**:
  - `ARCH-001`: Controller-to-repository layer bypass prevention.
  - `ARCH-002`: Domain-to-web dependency inversion prevention.
  - `ARCH-003`: Dependency cycle detection (Johnson's algorithm) split into `IMPORT`, `INHERITANCE`, and `CALL`.
  - `ARCH-004`: Required authorization annotations on secured endpoints.
- **Contract Verification**: Static producer-consumer schema checking across federated snapshots $S_p$ and $S_c$. Fails closed on snapshot drift.

### Pillar VI: Native GitIngest Engine (`devlensx/ingest.py`)
- Bundles any GitHub repository or local folder into a prompt-ready LLM digest.
- **SSRF Protection**: Strictly allows `github.com`. Rejects non-GitHub domains and path traversal attempts with HTTP 400.
- **Zero Double-Cloning**: Ingested repos are cached and can be fed straight into `Pipeline.analyze()` via `/api/analyze/from-ingest`.
- **Live Filtering**: Generates ASCII trees, calculates tokens (`tiktoken` `cl100k_base`), and supports interactive file unchecking with live token recalculation.

---

## 3. Complete REST API Endpoint Directory

| Method | Endpoint | Description | Request Payload / Params |
|---|---|---|---|
| `POST` | `/api/analyze` | Run full intelligence analysis on repo | `{ "repo_path": str }` |
| `POST` | `/api/analyze/from-ingest` | Analyze cached repo from ingest | `{ "ingest_id": str, "url": str }` |
| `POST` | `/api/ingest` | Native GitIngest prompt bundler | `{ url, branch?, include_patterns?, ... }` |
| `GET` | `/api/ingest/{id}/digest` | Download full text digest | None (`text/plain` attachment) |
| `GET` | `/api/governance/rules` | List active architectural rules | None |
| `POST` | `/api/governance/rules` | Create custom architectural rule | `{ rule_id, type, scope, ... }` |
| `POST` | `/api/governance/evaluate` | Run rule evaluation on snapshot | `{ snapshot_id, rules? }` |
| `POST` | `/api/governance/contracts/verify`| Verify producer-consumer contract | `{ producer_snapshot, consumer_snapshot }` |
| `POST` | `/api/governance/demo/seed` | Seed evaluation demo governance rules | None |
| `GET` | `/api/wiki/tree` | Hierarchical DeepWiki page tree | Query: `?run_id=...` |
| `GET` | `/api/wiki/page/{page_id}` | Fetch structured DeepWiki article | None |
| `POST` | `/api/wiki/digest` | Legacy digest endpoint (uses native engine)| `{ source, max_file_size, ... }` |
| `POST` | `/api/copilot/ask` | Ask conversational assistant with citations | `{ query, context_files, ... }` |
| `POST` | `/api/debug/analyze` | Analyze stack trace against graph | `{ stacktrace: str }` |
| `GET` | `/api/codemap` | Get ranked components & blast radius | None |
| `POST` | `/codereview/review-repo` | Run Code Turtle PR review | `{ diff?: str, repo_path?: str }` |
| `GET` | `/api/health` | System health & observability status | None |

---

## 4. Frontend Component & Routing Directory

| Route | View Component | Nav Group | Primary Features |
|---|---|---|---|
| `/overview` | `OverviewView.tsx` | Repository | Intelligence score, health radar, architecture briefings |
| `/ingest` | `IngestView.tsx` | Repository | Native GitIngest bundler, collapsible tree, live tokens |
| `/wiki` | `WikiView.tsx` | Understand | DeepWiki documentation, architecture diagrams, citations |
| `/codemap` | `CodemapView.tsx` | Understand | Interactive codebase tour, blast-radius component rank |
| `/architecture`| `ArchitectureView.tsx`| Understand | Layer dependencies, coupling graph, modularity analysis |
| `/explorer` | `ExplorerView.tsx` | Explore | Symbol browser, file inspector, call graph visualizer |
| `/ai-assistant`| `AIAssistantView.tsx`| AI Assistant | Grounded copilot, where-to-edit recommendations |
| `/code-turtle` | `CodeTurtleView.tsx` | Code Review | Senior PR reviewer, inline code editor, 1-click diffs |
| `/reviews` | `ReviewsView.tsx` | Code Review | Security audit, vulnerability tracker, findings ledger |
| `/changelog` | `ChangeImpactView.tsx` | Code Review | 4-tier blast-radius cascade, verified vs. suggestion zones |
| `/debug` | `DebugView.tsx` | Code Review | Grounded stack trace root-cause analysis |
| `/governance` | `GovernanceView.tsx` | System | Rule evaluation, cycle classification, contract verification |
| `/evaluation` | `EvaluationView.tsx` | System | Golden benchmark lab, precision/recall metrics |
| `/settings` | `SettingsView.tsx` | System | API keys, LLM providers (Gemini, OpenAI), theme |

---

## 5. Execution, Build & Test Commands

```bash
# 1. Start Backend API Daemon (Port 8000)
python run_devlensx.py api

# 2. Start Frontend Dev Server (Port 5173)
cd web && npm run dev

# 3. Build Frontend for Production (TypeScript + Vite)
cd web && npm run build

# 4. Run Pytest Suite (Ignores eval_repos & reference_repos via pytest.ini)
pytest tests/test_native_ingest.py
pytest tests/test_p5a_governance_rules.py tests/test_p5b_contracts.py tests/test_p5c_delivery_mcp_api.py

# 5. Native CLI Codebase Ingest
python run_devlensx.py ingest https://github.com/fastapi/fastapi -o digest.txt
```
