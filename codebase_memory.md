# Codebase Memory & Master System Intelligence — DevLensX

> **Permanent Brain & Comprehensive Architecture Document for DevLensX**
> **Product Identity:** *DevLensX — Understand, Debug, Build, and Review Any Codebase with Evidence.*
> *Consolidated Single-Source-of-Truth Codebase Memory File*
> *Last Updated: 2026-09-16*

---

## 1. Project Overview & Business Purpose

### Product Positioning
**DevLensX — Understand, Debug, Build, and Review Any Codebase with Evidence.**

DevLensX is an evidence-verified, polyglot software engineering intelligence platform. Traditional AI coding tools (Copilot, Cursor, ChatGPT) operate statelessly over isolated file snippets and frequently fabricate non-existent classes, methods, or API contracts. DevLensX solves this with grounded verification.

> [!IMPORTANT]
> **DevLensX Non-Negotiable Invariant:**
> *DevLensX must never require the user to understand the repository's implementation architecture before understanding the software.*
> *Implementation structure is evidence used by DevLensX to construct an understandable model; it is not the model presented to the user.*

### Core Product Philosophy
**DevLensX adapts its understanding to the repository's actual architecture — it never forces rigid layer assumptions (`Controller -> Service -> Repository`).**

Whether a repository is Java/Spring, Python/FastAPI, Node/Express, Next.js, Go, Rust, C#, a monorepo, a CLI tool, or an unstructured script, DevLensX translates code into human understanding through Progressive Disclosure:

$$\text{CODE} \longrightarrow \text{STRUCTURE} \longrightarrow \text{BEHAVIOR} \longrightarrow \text{CAPABILITIES} \longrightarrow \text{BUSINESS FLOWS} \longrightarrow \text{PLAIN-ENGLISH MAP}$$

---

## 2. Parser Architecture — Universal Repository Model (URM)

### Overview
DevLensX uses a **Tree-sitter powered polyglot parser** with a **Universal Repository Model (URM)** as the language-agnostic output format. The old `javalang`-only parser is now the Java-specific adapter within this larger framework.

```
                    ┌──────────────────────────┐
                    │      REPOSITORY INPUT     │
                    │ ZIP / GitHub / Local Repo │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   LANGUAGE DETECTOR       │
                    │ devlensx/shared/types.py  │
                    │ 21 languages via extension│
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼─────────────────────────┐
          ▼              ▼              ▼             ▼     ▼
    Java Adapter   Python Adapter  TS Adapter   Go Adapter  ...
    (32 KB)        (35 KB)         (42 KB)      (21 KB)
          │              │              │             │
          └──────────────┼─────────────┘─────────────┘
                         ▼
            UNIVERSAL REPOSITORY MODEL (URM)
            devlensx/urm/models.py
            UniversalRepositoryModel
            {symbols, relationships, endpoints, configurations, frameworks}
```

### Supported Languages (`devlensx/shared/types.py` — `SupportedLanguage` enum)
```
Java, Python, TypeScript, JavaScript, Go, Rust, C#, C++, C,
PHP, Ruby, Kotlin, Swift, Scala, Dart, Bash, Lua,
JSON, TOML, YAML, HTML, CSS, Dockerfile
```

### Language Adapters (`devlensx/urm/adapters/`)
| Adapter | Size | Primary Frameworks Detected |
|---|---|---|
| `java_adapter.py` | 32 KB | Spring Boot, Maven, Gradle, JUnit |
| `python_adapter.py` | 35 KB | FastAPI, Flask, Django, PyTorch, YOLO |
| `typescript_adapter.py` | 42 KB | React, Next.js, Express, NestJS, Vite |
| `go_adapter.py` | 21 KB | Gin, Echo, goroutines, interfaces |
| `rust_adapter.py` | 23 KB | Traits, impl blocks, Cargo |
| `csharp_adapter.py` | 28 KB | .NET, ASP.NET, dependency injection |
| `cpp_adapter.py` | 31 KB | Classes, namespaces, templates |

### Universal Repository Model Data Schema (`devlensx/urm/models.py`)
```python
UniversalRepositoryModel:
  repository_id: str
  name: str
  primary_language: str
  languages: Dict[str, float]        # language → percentage
  frameworks: List[URMFramework]
  symbols: List[URMSymbol]           # every code symbol
  relationships: List[URMRelationship]
  endpoints: List[URMEndpoint]
  configurations: List[URMConfiguration]  # JSON, YAML, TOML, Dockerfile etc.
```

**`URMSymbol` — 22 kinds (replaces old Java-specific "stereotype" string):**
```
MODULE, PACKAGE, NAMESPACE, CLASS, STRUCT, INTERFACE, TRAIT,
ENUM, TYPE_ALIAS, FUNCTION, METHOD, CONSTRUCTOR, FIELD, PROPERTY,
VARIABLE, CONSTANT, PARAMETER, IMPORT, EXPORT, ANNOTATION,
DECORATOR, GENERIC_PARAM
```

**`RelationshipType` — 14 types:**
```
IMPORTS, CALLS, DEPENDS_ON, EXTENDS, IMPLEMENTS, CONTAINS,
DEFINES, REFERENCES, RETURNS, ACCEPTS, THROWS, DECORATES,
ANNOTATES, ROUTES_TO, CONFIGURES
```

Each `URMSymbol` carries a `SourceLocation` (file, line_start, line_end) enabling exact line-level citations everywhere in the platform.

### Legacy Compatibility
`URMSymbol.to_legacy_dict()` converts to the old dict format that `critic_engine.py`, `architecture_agent.py`, and other modules still use. This ensures backward compatibility during the URM migration.

---

## 3. Platform Layered Architecture

```
                                  DEV LENS X
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           │                                                     │
    FACT / EVIDENCE ENGINE                               AI REASONING ENGINE
(What is actually in the repo?)                      (What does it mean & what to do?)
           │                                                     │
    ┌──────┴──────────────┐                               ┌──────┴──────────────┐
    │ Tree-sitter URM     │                               │ LLM Synthesis       │
    │ KuzuDB Graph Store  │                               │ Intent Planner      │
    │ FAISS Embeddings    │                               │ Session Context     │
    │ Git Churn Facts     │                               │ Feature Clusters    │
    │ Semgrep Rules       │                               │ AI Suggestions      │
    └──────┬──────────────┘                               └──────┬──────────────┘
           │                                                     │
           └──────────────────────────┬──────────────────────────┘
                                      │
                                      ▼
                           FAIL-CLOSED CRITIC AGENT
                        (Verifies Evidence Threshold)
                                      │
                                      ▼
                        DEVLENSX DEVELOPER WORKSPACE
  [🚀 Overview] [📖 Wiki] [💬 Ask] [🐛 Debug] [🔨 Build] [🐢 Review] [🗺️ Explore]
```

### 5-Layer Operational Pipeline Architecture
1. **Layer 1 — Repository Ingestion (`POST /api/analyze`, local path discovery):** Extracts archive into workspace, validates file layout, detects language mix.
2. **Layer 2 — Tree-sitter Polyglot AST Analysis (`devlensx/parser/__init__.py`):** Parses all source files using Tree-sitter with 7 language adapters. Outputs `UniversalRepositoryModel` with language-agnostic `URMSymbol` nodes.
3. **Layer 3 — Structural Knowledge Graph (`KuzuDB`):** Persists `JavaClass` nodes (name pending rename to `RepositorySymbol`) and relational edges (`DEPENDS_ON`, `EXTENDS`, `IMPLEMENTS`).
4. **Layer 4 — Semantic RAG Vector Index (`FAISS`):** Indexes dense 384-dimensional code embeddings. Fuses Cypher graph paths with semantic vectors using weighted scoring ($0.6 \times \text{VectorSim} + 0.4 \times \text{GraphProximity}$).
5. **Layer 5 — Fail-Closed Critic Agent:** Evaluates raw findings across Graph, AST, Structural Path, and Semgrep evidence channels. Rejects findings scoring $< 50.0\%$ evidence coverage.

### Tri-Database Role Separation (Critical distinction)
- **SQLite (Application State):** Manages users, repositories, analysis runs, findings, conversations, messages, and audit logs (*"Who is the user and what has happened in the app?"*).
- **KuzuDB (Structural Knowledge Graph):** Embedded C++ property graph storing `JavaClass` nodes and structural dependency edges (*"How is the software itself connected?"*).
- **FAISS (Semantic Vector Index):** In-process dense vector index for fast semantic similarity search (*"What code is semantically relevant to this question?"*).

### Score Formula (Locked 5-Weighted Formula)
The Repository Intelligence Score formula is strictly locked in `devlensx/config.py` (`SCORE_WEIGHTS`):
$$\text{Score} = 0.30 \times \text{Architecture} + 0.25 \times \text{Security} + 0.20 \times \text{Maintainability} + 0.15 \times \text{Coupling} + 0.10 \times \text{EvidenceCoverage}$$

- **Architecture:** 30% — Average of Maintainability and Coupling sub-scores
- **Security:** 25% — 100 minus penalties per High/Medium security issue
- **Maintainability:** 20% — 100 minus 15 points per God Class (>15 methods)
- **Coupling:** 15% — 100 minus 10 points per High Blast Radius Component
- **Evidence Coverage:** 10% — Average Evidence Coverage Score across verified findings

### Claim Taxonomy (Frozen)
- 🟢 `VERIFIED` — AST-confirmed structural fact (2+ of 4 evidence sources passed)
- 🔵 `AI_SUGGESTION (UNVERIFIED)` — LLM proposal, not evidence-backed
- 🔴 `INSUFFICIENT EVIDENCE` — Critic rejected due to < 50% evidence coverage score

---

## 4. The 7-Layer Repository Brain Model
1. **Layer 1 — Repository Identity & Purpose:** Identifies tech stack, project identity, and primary purpose (*"What is this and why does it exist?"*).
2. **Layer 2 — Capability Map:** Groups components into discovered business capabilities (e.g., Accounts, Appointments, Payments) without hardcoded layer assumptions.
3. **Layer 3 — User & Business Flows:** Maps step-by-step execution flows (*"Register -> Validate -> Hash Password -> Store User"*).
4. **Layer 4 — Execution Understanding:** Translates technical interactions into plain-English runtime execution flows.
5. **Layer 5 — Code-Level Evidence:** Exposes exact source files, classes, methods, and routes with 🟢 **VERIFIED BY AST** proof.
6. **Layer 6 — Change Impact Understanding:** Explains how modifying a component affects user-facing business flows via reverse graph traversal.
7. **Layer 7 — AI Reasoning & Grounded Suggestions:** Provides contextual AI guidance with clear 🔵 **AI SUGGESTION (UNVERIFIED)** labeling.

---

## 5. Technology Detection & Tech Stack

### Frontend Architecture
- **Framework:** React 19 + TypeScript + Vite 8
- **Styling:** Vanilla TailwindCSS + Custom CSS glassmorphism tokens (`index.css`, `App.css`)
- **Icons:** `lucide-react`
- **Graph Canvas:** `@xyflow/react` (interactive node drag, zoom, pan)
- **Diagrams:** `mermaid` (rendered client-side, `securityLevel: 'strict'`)
- **Build Tooling:** `tsc -b && vite build`

### Backend Architecture
- **Language & Framework:** Python 3.13 & FastAPI / Uvicorn
- **Parser Engine:** Tree-sitter with 7 language adapters (Java, Python, TypeScript, Go, Rust, C#, C++)
- **Legacy Java Parser:** `javalang` (now the Java adapter within URM, not primary parser)
- **Graph Database:** `kuzu` (0.4.0+) embedded C++ property graph database
- **Vector Index / RAG:** `faiss-cpu` (1.7.4+) for 384-dimensional dense semantic embeddings
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **LLM Abstraction Layer:** `devlensx/llm/provider.py` supporting Gemini, OpenAI, OpenRouter, Azure OpenAI, Groq, Ollama, Offline
- **Git Integration:** `gitpython` for auto-clone and git churn facts
- **Static Analysis:** `semgrep` (optional, 4th evidence source for Critic)

---

## 6. Repository Discovery & Folder Structure

```
DevLensX/
├── .devlensx-runtime/           # Runtime data & temp storage
├── .gemini/                     # Gemini system instructions
│   └── settings.json
├── devlensx/                    # Core Python Backend Package (35 sub-modules)
│   ├── agents/                  # Multi-agent analysis engines
│   │   ├── architecture_agent.py  # God-class & coupling scanner
│   │   ├── security_agent.py      # Secrets & endpoint auditor
│   │   ├── change_impact_agent.py # Blast-radius simulation
│   │   └── llm_client.py
│   ├── api/                     # FastAPI REST API (13+ routers)
│   │   ├── main.py              # Central REST server & router registration
│   │   └── routes/              # auth, repositories, copilot, debug, git,
│   │                            #   wiki, evidence, diagrams, chat, workspace,
│   │                            #   incremental, codemap, codereview, evaluation
│   ├── build/                   # Build studio subsystem
│   ├── capability_registry.yaml # Business capability definitions
│   ├── chat/                    # Persistent chat session management
│   ├── codemap.py               # Code map generator (12 KB)
│   ├── codereview.py            # CodeTurtle PR review engine (56 KB)
│   ├── config.py                # Locked score weights & thresholds
│   ├── core/                    # JWT auth, security helpers, XSS sanitization
│   ├── critic/                  # Fail-Closed Critic Grounding Engine
│   │   ├── critic_engine.py     # 4-source evidence scoring & rejection
│   │   └── claim_verifier.py    # ClaimVerifierEngine (tech-keyword hallucination guard)
│   ├── dashboard/               # Streamlit dashboard alternative UI
│   ├── db/                      # SQLite ORM models (users, repos, runs, findings)
│   ├── debug/                   # Stack trace debugger subsystem
│   ├── deep_reasoning.py        # Deep reasoning engine (48 KB) — backbone
│   ├── diagrams/                # Mermaid diagram generators
│   ├── documentation/           # Documentation generator subsystem
│   ├── evaluation/              # Evaluation benchmarking subsystem
│   ├── evaluation.py            # Benchmark orchestrator (N=73)
│   ├── evidence/                # Evidence reference subsystem
│   ├── git/                     # Git churn & history facts
│   ├── graph/                   # KuzuDB graph store
│   │   ├── kuzu_store.py        # Embedded C++ graph (Prepared Statements)
│   │   └── neo4j_store.py       # Optional remote Neo4j fallback
│   ├── impact/                  # Change impact subsystem
│   ├── incremental/             # Incremental re-analysis subsystem
│   ├── llm/                     # Unified LLM Abstraction Layer
│   │   └── provider.py          # Gemini, OpenAI, OpenRouter, Azure, Groq, Ollama
│   ├── observability/           # Request correlation & structured logging
│   ├── parser/                  # Polyglot Parser Package (entry point)
│   │   ├── __init__.py          # parse_repo() — URM-based orchestrator
│   │   ├── java_parser.py       # Legacy javalang AST parser (still used for eval)
│   │   └── treesitter_parser.py # Tree-sitter parser wrapper
│   ├── performance/             # Performance profiling subsystem
│   ├── polyglot/                # Polyglot models & validator
│   ├── rag/                     # RAG subsystem
│   ├── reasoning/               # Reasoning subsystem
│   ├── recommendation/          # Recommendation Synthesizer & Score Engine
│   ├── repository_memory/       # Master Pipeline Orchestrator (RepositoryIntelligenceEngine)
│   ├── retrieval/               # GraphRAG & Hybrid Retrieval
│   │   ├── vector_store.py      # FAISS + MiniLM vector indexing
│   │   └── hybrid_retriever.py  # Cypher triples + FAISS fusion
│   ├── review/                  # DiffAnalyzer for PR review diffs
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Shared service layer
│   ├── shared/                  # Shared types across parser & adapters
│   │   └── types.py             # SupportedLanguage enum (21 langs), ParseResult
│   ├── understanding/           # Understanding Subsystem
│   │   ├── capability_detector.py  # Business domain discovery
│   │   ├── flow_detector.py        # Execution flow & architecture detection
│   │   ├── wiki_generator.py       # WikiGenerator (line-level citations, TOC)
│   │   ├── intelligence/           # Feature memory & capability intelligence
│   │   └── profiling/
│   │       └── repository_profiler.py  # Polyglot manifest inspector
│   ├── urm/                     # Universal Repository Model
│   │   ├── models.py            # UniversalRepositoryModel, URMSymbol, etc.
│   │   └── adapters/            # 7 language adapters
│   │       ├── base.py
│   │       ├── java_adapter.py    (32 KB)
│   │       ├── python_adapter.py  (35 KB)
│   │       ├── typescript_adapter.py (42 KB)
│   │       ├── go_adapter.py      (21 KB)
│   │       ├── rust_adapter.py    (23 KB)
│   │       ├── csharp_adapter.py  (28 KB)
│   │       └── cpp_adapter.py     (31 KB)
│   ├── wiki.py                  # DeepWiki generator engine (55 KB / 1165 lines)
│   ├── wiki_depth.py            # DeepWiki depth pipeline (25 KB / 559 lines)
│   └── workspace/               # Workspace management
├── web/                         # React Frontend SPA
│   ├── src/
│   │   ├── components/          # 37 React UI components
│   │   ├── App.tsx              # Layout router & global state
│   │   ├── apiClient.ts         # REST API client + fallback mocks
│   │   ├── store.ts             # Zustand global app store
│   │   ├── wikiContext.tsx      # Wiki page tree context
│   │   ├── workspaceContext.tsx # Workspace & repo context
│   │   ├── evidence.ts          # Evidence verdict types
│   │   └── types.ts             # TypeScript interfaces
│   └── package.json             # React 19, Vite 8, @xyflow/react, mermaid
├── run_devlensx.py              # CLI Launcher (analyze, query, api, web)
├── codebase_memory.md           # Master Codebase Memory (This File)
├── architecture.md              # System pipeline architecture specification
├── research_paper_framework.md  # Academic paper framework & evaluation metrics
├── eval_dataset_spring-petclinic.json  # Locked benchmark N=23
├── eval_dataset_mybatis-3.json         # Locked benchmark N=25
├── eval_dataset_dubbo.json             # Locked benchmark N=25
├── evaluate_saved_json_fast.py  # Dataset benchmark suite
├── requirements.txt             # Python dependencies
└── docker-compose.yml           # Multi-container production deployment
```

---

## 7. Core Subsystems — Deep Descriptions

### A. Parser Engine (`devlensx/parser/`)
Entry point: `parse_repo(repo_path)` in `devlensx/parser/__init__.py`.
- Uses `get_treesitter_parser()` (from `devlensx/shared/types.py`) to parse all files.
- Routes each `ParseResult` through the appropriate adapter via the adapter registry.
- Aggregates `URMSymbol`, `URMRelationship`, `URMEndpoint`, `URMConfiguration`, `URMFramework` into `UniversalRepositoryModel`.
- Tracks per-language file counts and calculates language percentages.
- `java_parser.py` is still used for the benchmark evaluation pipeline (N=73 dataset).

### B. Knowledge Graph Engine (`devlensx/graph/`)
- `kuzu_store.py`: Embedded C++ property graph using Kuzu. **Optimized with Prepared Statements** reducing graph build from ~2142ms to **967ms** (2.2× speedup).
- Node type: `JavaClass` (name being migrated to `RepositorySymbol`). Fields: `name`, `stereotype`, `package`, `file`, `is_test`, `incoming_count`, `outgoing_count`, `method_count`, `endpoint_count`.
- Edge types: `DEPENDS_ON`, `EXTENDS`, `IMPLEMENTS`.
- Key queries: `query_change_impact(class_name)`, `query_blast_radius(limit)`, `query_architecture_flow()`, `query_subgraph_triples()`.

### C. Hybrid Retrieval Engine (`devlensx/retrieval/`)
- `vector_store.py`: Generates 384-dim dense semantic embeddings via `all-MiniLM-L6-v2`, indexes via `faiss.IndexFlatL2`.
- `hybrid_retriever.py`: Fuses FAISS vector similarity with KuzuDB 2-hop graph traversal. Score = $0.6 \times \text{VectorSim} + 0.4 \times \text{GraphProximity}$.

### D. Multi-Agent Analyzer Suite (`devlensx/agents/`)
- `architecture_agent.py`: God-classes (>15 methods), coupling bottlenecks (≥3 incoming dependents), dependency chain extraction.
- `security_agent.py`: Hardcoded secret scanning, unprotected REST endpoints (missing `@PreAuthorize`), Semgrep CLI integration.
- `change_impact_agent.py`: Reverse graph traversal blast radius (HIGH ≥15, MEDIUM 5–15, LOW <5).

### E. Fail-Closed Critic Grounding Engine (`devlensx/critic/`)
- `critic_engine.py`: 4-source verification per finding:
  1. **Graph Check** — node + reverse edges in KuzuDB
  2. **AST Check** — exact method/field/endpoint/dependency/inheritance verified (6 adversarial sub-checks)
  3. **Semgrep Check** — independent static analysis confirmation
  4. **Structural Check** — file path normalized match
- Evidence Coverage Score = (verified_sources / 4) × 100. ≥50% → VERIFIED; <50% → REJECTED.
- `claim_verifier.py`: `ClaimVerifierEngine` — detects hallucinated infrastructure keywords (Redis, Kafka, RabbitMQ, Elasticsearch, MongoDB, Neo4j) in wiki/review claims.

### F. DeepWiki System (`devlensx/wiki.py` + `devlensx/wiki_depth.py`)

**`wiki.py` (1165 lines) — Primary wiki generator:**
- Generates 5 wiki page types: Overview, Architecture, Module pages (one per package), API Reference (grouped by controller), Change Impact.
- 3 deterministic Mermaid diagram types (topology never LLM-generated): `render_system_dependency_mermaid()`, `render_module_class_diagram()`, `render_sequence_diagram()`.
- Thread-safe `WikiCache` keyed by `repo_id::commit_hash::analysis_id` with per-page invalidation.
- Every wiki section carries a `verdict` badge ("Verified" / "Unverified") via `_lightweight_critic_check()`.
- XSS prevention: all headings via `wiki_heading_sanitize()` (html.escape, 200 char), all content via `wiki_content_sanitize()` (html.escape, 2000 char).
- Line-level AST citations: `{nodeId, file, line_start, line_end, citation_ref}` on every claim.

**`wiki_depth.py` (559 lines) — DeepWiki-grade depth pipeline:**
- Multi-pass generation: Structure pass → Retrieval slice → Pass1 (facts) → Pass2 (LLM explanation) → Pass3 (critique/tighten) → Cross-link pass → Progressive disclosure.
- `build_overview_deep()` generates a 6-part overview: "what this is", "architecture at a glance", "key components by centrality", "request flow", "tech stack", "where next".
- `critique_section()` cuts sentences with <2 grounding tokens in fact set.
- `crosslink_markdown()` auto-links entity mentions to their module/API page IDs.
- `overview_depth_check()` enforces minimum 8 distinct nodeId/findingId refs on Overview page.

**`devlensx/understanding/wiki_generator.py`** — Subsystem-level wiki generator integrating with `RepositoryProfiler` and `CapabilityDetector`.

### G. CodeTurtle — AI Code Review Engine (`devlensx/codereview.py`)
DevLensX's free alternative to CodeRabbit for evidence-verified PR review.

**`CodeRabbitEngine` class (1270 lines):**
- Multi-provider: Gemini, OpenAI, Azure OpenAI, OpenRouter, Groq, Ollama, Offline fallback. Default: `gemini`.
- **Prompt Injection Prevention (P0-A):** Diffs wrapped in `<<<UNTRUSTED_DIFF_BEGIN>>>` / `<<<UNTRUSTED_DIFF_END>>>` trust boundary in system prompt.
- Resource bounds: `MAX_DIFF_CHARS = 120,000`, `MAX_DIFF_LINES = 4,000`.
- **4-Verdict system:** `VERIFIED`, `AI_SUGGESTION`, `INSUFFICIENT_EVIDENCE`, `NOT_VERIFIED`.
- `severity` (CRITICAL/HIGH/MEDIUM/LOW) is **always independent** of `verdict` (evidentiary status).
- `verify_candidates()` runs every LLM finding through `ClaimVerifierEngine`: nodeId resolution → VERIFIED + refs; free-text → symbol match → AI_SUGGESTION; no match → INSUFFICIENT.
- `changed_symbol_map()` uses `DiffAnalyzer` to stamp `changed_line_start/end` on findings whose primary symbol was touched by the diff.
- Streaming support via `stream_review()` async generator.
- **P1-H invariant (enforced in frontend):** A VERIFIED badge with no `evidence_refs` must never render as VERIFIED.

### H. Deep Reasoning Engine (`devlensx/deep_reasoning.py` — 48 KB)
Central utility used by wiki generation, agent analysis, and graph store. Key functions:
- `build_method_index(classes)` — builds `{class_name: [method_node, ...]}` from URM class list.
- `prod_methods(method_index, name)` — filters to production (non-test) methods only.
- `is_prod_component(c)` — returns True for non-test, non-config, non-dunder symbols.
- `simple_name(qname)` — extracts simple class name from fully-qualified name.
- `handler_matches(handler_token, class_name)` — matches endpoint handler tokens to class names.
- `ctor_params(method_index, name)` — extracts constructor parameter list for DI detection.
- `build_deep_reasoning()` / `DeepReasoningEngine` — full reasoning engine class.

### I. Understanding Subsystem (`devlensx/understanding/`)
- `capability_detector.py` (`CapabilityDetector`): Groups classes into business domains from package structure. Language-agnostic (uses package strings not Java-only logic).
- `flow_detector.py` (`FlowDetector`, `ArchitectureDetector`): Detects execution flows from Controller→Service chains. `ArchitectureDetector` classifies repo as Modular Layered, Feature-Oriented, or Concentrated.
- `profiling/repository_profiler.py` (`RepositoryProfiler`): Reads real manifests (pom.xml, package.json, requirements.txt, Cargo.toml, go.mod, pyproject.toml, build.gradle). Detects frameworks, databases, entrypoints, and classifies architectural archetype (FRONTEND_UI, WEB_BACKEND, CLI_ENGINE, FRAMEWORK_LIBRARY, DATA_ML_SYSTEM, MODULAR_APPLICATION).
- `intelligence/feature_memory.py`: Feature memory subsystem for discovered capabilities.

### J. Unified LLM Abstraction Layer (`devlensx/llm/provider.py`)
Providers supported:
| Provider Class | Backend | Default Model |
|---|---|---|
| `GeminiProvider` | Google Gemini | `gemini-1.5-flash` |
| `OpenAIProvider` | OpenAI API | `gpt-4o-mini` |
| `AzureOpenAIProvider` | Azure OpenAI | deployment-defined |
| `OpenRouterProvider` | OpenRouter | configurable |
| `GroqProvider` | Groq | configurable |
| `OllamaProvider` | Local Ollama | configurable |
| `OfflineProvider` | Deterministic templates | N/A |

---

## 8. Frontend Component Inventory (37 Components)

All components in `web/src/components/`:

| Component | Size | Purpose |
|---|---|---|
| `WikiView.tsx` | 38 KB | DeepWiki documentation viewer (5 categories, Mermaid, Copilot Q&A drawer) |
| `CodeTurtleView.tsx` | 32 KB | CodeRabbit-style PR review (streaming, evidence badges, diff viewer) |
| `ExplorerPage.tsx` | 30 KB | File & code browser |
| `OtherViews.tsx` | 27 KB | Misc views aggregator |
| `DocsPage.tsx` | 24 KB | Documentation generator workspace |
| `LandingPage.tsx` | 24 KB | Landing/onboarding page |
| `OverviewView.tsx` | 25 KB | Main overview workspace |
| `KnowledgeGraphView.tsx` | 19 KB | @xyflow interactive node graph |
| `ArchitecturePage.tsx` | 15 KB | Architecture graph workspace |
| `GalaxyConstellationGraph.tsx` | 15 KB | 3D galaxy-style class graph |
| `Header.tsx` | 14 KB | Global header with provider status pill |
| `ChatPanel.tsx` | 10 KB | Chat session panel |
| `DiagramInspectionDrawer.tsx` | 10 KB | Diagram hover-inspect panel |
| `CodemapView.tsx` | 9 KB | Code map visualization |
| `InteractiveDiagram.tsx` | 9 KB | Mermaid interactive diagram wrapper |
| `CommandPalette.tsx` | 8 KB | Cmd+K command palette |
| `Sidebar.tsx` | 10 KB | Navigation sidebar |
| `GlassPanel.tsx` | 4 KB | Glassmorphism panel component |
| `Badge.tsx` | 3 KB | Risk / Verification / Category badges |
| `Skeleton.tsx` | 3 KB | Loading skeleton screens |
| `TerminalWindow.tsx` | 4 KB | Terminal-style output window |
| `SourceViewer.tsx` | 4 KB | Source code viewer with line highlighting |
| `AnalyzingScreen.tsx` | 3 KB | Analysis progress screen |
| `EvidenceBadge.tsx` | ~1 KB | Evidence verdict badge (VERIFIED/AI_SUGGESTION/etc.) |
| `EvidenceCitation.tsx` | 2 KB | Inline file:line citation component |
| `EvidencePanel.tsx` | 2 KB | Evidence panel drawer |
| `EmptyState.tsx` | ~2 KB | Empty state placeholder |
| `ErrorBoundary.tsx` | ~1 KB | React error boundary |
| `StatusIndicator.tsx` | ~0.5 KB | Provider online/offline indicator |
| `ArchitectureView.tsx` | ~1 KB | Architecture view wrapper |
| `ChangeImpactView.tsx` | stub | Build Studio (stub, integrated into OverviewView) |
| `ReviewsView.tsx` | stub | Reviews view wrapper (stub) |
| `EvaluationView.tsx` | stub | Research Evaluation Lab (stub) |
| `SettingsView.tsx` | stub | Settings view wrapper (stub) |
| `ExplorerView.tsx` | ~1 KB | Explorer view wrapper |
| `CodeRabbitView.tsx` | stub | Legacy code review stub |
| `index.ts` | ~0.6 KB | Component barrel export |

---

## 9. API Routes (13 Registered Routers + Core Routes)

### Core Routes in `devlensx/api/main.py`
| Method | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Health check + version |
| `POST` | `/api/analyze` | Full 5-stage pipeline (parse → graph → agents → critic → score) |
| `GET` | `/api/score` | Latest Repository Intelligence Score & sub-scores |
| `POST` | `/api/retrieval` | Hybrid GraphRAG retrieval (Cypher + FAISS) |
| `GET` | `/api/change-impact/{class_name}` | Blast radius for a class |

### Registered Routers (via `devlensx/api/routes/`)
| Router | Prefix | Key Endpoints |
|---|---|---|
| `auth_router` | `/api/auth` | Login, register, JWT token |
| `repositories_router` | `/api/repositories` | List, create, delete repos |
| `copilot_router` | `/api/copilot` | `/ask`, `/decision`, `/planner/classify` |
| `debug_router` | `/api/debug` | `/trace` — stack trace → AST nodes |
| `git_router` | `/api/git` | `/churn` — commit facts per file |
| `wiki_router` | `/api/wiki` | List pages, fetch page, copilot Q&A |
| `evidence_router` | `/api/evidence` | Evidence reference resolution |
| `diagrams_router` | `/api/diagrams` | Mermaid diagram generation |
| `chat_router` | `/api/chat` | Persistent chat sessions |
| `workspace_router` | `/api/workspace` | Workspace management |
| `incremental_router` | `/api/incremental` | Incremental re-analysis |
| `codemap_router` | `/api/codemap` | Code map generation |
| `codereview_router` | `/api/reviews` | `/pr-review` — CodeTurtle streaming review |
| `evaluation_router` | `/api/evaluation` | Benchmark evaluation |

---

## 10. Frontend Navigation Structure (App.tsx)

| Tab Key | Component | Purpose |
|---|---|---|
| `overview` | `OverviewView.tsx` | Project briefing, 7-layer model, score, business flows |
| `wiki` | `WikiView.tsx` | DeepWiki: 5-category docs, Mermaid diagrams, copilot Q&A |
| `copilot` | `ChatPanel.tsx` | Grounded multi-turn Q&A assistant |
| `architecture` | `ArchitecturePage.tsx` | Interactive knowledge graph (galaxy + flow canvas) |
| `explorer` | `ExplorerPage.tsx` | File & symbol browser |
| `codemap` | `CodemapView.tsx` | Code map visualization |
| `reviews` | `CodeTurtleView.tsx` | CodeTurtle PR review engine |
| `docs` | `DocsPage.tsx` | Auto-documentation generator |
| `debug` | (in OtherViews) | Stack trace debugger |
| `settings` | (in OtherViews) | LLM provider & API key management |

---

## 11. Database Architecture & Graph Schemas

### KuzuDB Property Graph Schema (`devlensx/graph/kuzu_store.py`)
Embedded C++ property graph database stored in temp directory (per-analysis UUID).

#### Node Table: `JavaClass` *(note: name pending migration to `RepositorySymbol`)*
- `name` (STRING, PRIMARY KEY)
- `stereotype` (STRING): Controller, Service, Repository, Entity, Configuration, Test, Component, etc.
- `package` (STRING)
- `file` (STRING)
- `is_test` (BOOLEAN)
- `incoming_count` (INT64): downstream dependent count
- `outgoing_count` (INT64): upstream dependency count
- `method_count` (INT64)
- `endpoint_count` (INT64)

#### Edge Tables:
1. `DEPENDS_ON`: Injected dependencies
2. `EXTENDS`: Inheritance
3. `IMPLEMENTS`: Interface implementation

### SQLite Schema (`devlensx/db/`)
Tables: `users`, `repositories`, `analysis_runs`, `findings`, `conversations`, `messages`, `audit_logs`.

---

## 12. Key Files — Do Not Modify Lightly

| File | Why Critical |
|---|---|
| `devlensx/critic/critic_engine.py` | Fail-closed verification. Changing thresholds or checks breaks the 0.0% FRR guarantee. |
| `devlensx/config.py` | Locked score weights. Any change invalidates the N=73 benchmark baseline. |
| `devlensx/graph/kuzu_store.py` | Graph schema. Changing node/edge types requires full migration + re-index. |
| `devlensx/deep_reasoning.py` | Central utility used by agents, wiki, kuzu_store. API changes cascade everywhere. |
| `devlensx/llm/provider.py` | LLM gateway. All providers route through here — CodeTurtle, wiki, copilot, agents. |
| `devlensx/api/main.py` | Router registration. Adding/removing routers here affects all API consumers. |
| `web/src/App.tsx` | Global navigation state. Tab key changes break all tab routing. |
| `web/src/apiClient.ts` | All REST calls go through here. Function signature changes break all callers. |

---

## 13. Module Import Dependency Hierarchy

```
run_devlensx.py
        │
        ▼
devlensx/api/main.py
        │
┌───────┼───────────────────────────────────────────┐
▼       ▼                    ▼                      ▼
devlensx/repository_memory/  devlensx/critic/   devlensx/llm/
RepositoryIntelligenceEngine  CriticAgent        LLMProvider
        │                        │
┌───────┴───────┐                │
▼               ▼                │
devlensx/parser/  devlensx/graph/ │
parse_repo()      KuzuGraphStore  │
(URM-based)              │       │
        │                │       │
        └────────┬────────┘       │
                 ▼               │
        devlensx/retrieval/       │
        HybridContextRetriever   │
                 │               │
                 └───────────────┤
                                 ▼
                        devlensx/agents/
                        ArchitectureAgent
                        SecurityAgent
                        ChangeImpactAgent
                                 │
                                 ▼
                        devlensx/recommendation/
                        RecommendationEngine
                                 │
                                 ▼
                        devlensx/wiki.py + wiki_depth.py
                        devlensx/codereview.py
```

---

## 14. Fail-Closed Critic — Evidence Protocol

Every finding generated by any agent or LLM goes through `CriticAgent.verify_finding()`:

```
Finding Input
      │
      ├─→ [1] Graph Check:  class_name present in KuzuDB + has edges?
      ├─→ [2] AST Check:    6 adversarial sub-checks:
      │         A. Claimed method exists in class methods?
      │         B. Claimed field exists in class fields?
      │         C. Claimed endpoint exists in class endpoints?
      │         D. Claimed dependency exists in injected_deps?
      │         E. Claimed parent class matches actual extends?
      │         F. God-class: actual method_count > 15 AND >= claimed?
      ├─→ [3] Semgrep Check: Semgrep CLI confirmed (or skipped if uninstalled)
      └─→ [4] Structural Check: file path normalized match
                    │
                    ▼
      evidence_coverage_score = (passed / 4) * 100
      verdict = "VERIFIED" if ≥ 50.0% else "REJECTED"
```

**Evidence Coverage Score formula:**
$$\text{Evidence Coverage Score (\%)} = \left( \frac{\text{Verified Sources Count}}{4} \right) \times 100$$

> **Note:** In Windows environments without Semgrep CLI installed, `semgrep_check` is always `False`, capping maximum observed ratio at **3/4 (75.0%)**. Achieving 4/4 (100.0%) requires Semgrep in a Linux/WSL environment.

---

## 15. Performance & Benchmark Metrics

### Evaluation Dataset (N=73)
Tested on 3 real open-source Java repositories with manual expert annotation:

| Repository | Scale | N | TP/FP | Without-Critic Precision | With-Critic Precision | FP Rejection | FRR |
|---|---|---|---|---|---|---|---|
| Spring PetClinic | Small | 23 | 8/15 | 34.8% | 34.8% | 0.0% | **0.0%** |
| MyBatis-3 | Medium | 25 | 9/16 | 36.0% | 39.1% | 12.5% | **0.0%** |
| Apache Dubbo | Large | 25 | 12/13 | 48.0% | 54.5% | 23.1% | **0.0%** |
| **POOLED** | All | **73** | **29/44** | **39.7%** | **42.6%** | **11.4%** | **0.0%** |

**False Rejection Rate = 0.0%** — the Critic never incorrectly rejected a real bug across all 73 findings.

### Stage Timing Benchmarks
| Stage | PetClinic (48 files) | MyBatis-3 (1,370 files) | Dubbo (4,032 files) |
|---|---|---|---|
| AST Parsing | 0.49s | 18.23s | 226.18s |
| Graph Build (Kuzu) | 1.44s | 9.17s | 137.02s |
| Multi-Agent Scan | 0.17s | 0.21s | 0.26s |
| Critic Verification | 0.34s | 1.25s | 9.46s |
| **Total** | **2.45s** | **28.87s** | **6m 12.93s** |

---

## 16. Operational Rules & Verification Trust Model

1. **Defensible Grounding Principle:** DevLensX prevents unsupported repository claims from being classified as VERIFIED; ungrounded or ambiguous claims fail closed as AI_SUGGESTION or INSUFFICIENT_EVIDENCE.
2. **Never Assume:** Verify every structural claim against parsed AST and Kùzu graph data.
3. **Fail-Closed Verification:** Reject findings if target symbols, fields, or REST endpoints do not exist in parsed AST.
4. **Visual Separation:** Never present AI-suggested code next to a VERIFIED badge.
5. **Grounding ≠ Correctness:** DevLensX verifies structural evidence grounding, not semantic correctness. A structurally-grounded finding may still be a design tradeoff requiring human judgment.
6. **Evidence Trail Always:** Every VERIFIED finding must carry `evidence_refs` with file:line citations.
7. **Explicit-Action Only:** 1-click committable suggestions require explicit user application; no automatic code-writing.

---

## 17. System Verification Status

> **All Engineering Validation Milestones have been successfully executed and verified with zero regressions.**

| Step | Milestone | Status |
|---|---|---|
| 0 | Baseline Lock (benchmark datasets) | 🟢 PASSED |
| 1 | Ingestion & File Discovery | 🟢 PASSED |
| 2 | Core Pipeline (AST → KuzuDB → FAISS) | 🟢 PASSED |
| 3 | Repository Brain Consolidation | 🟢 PASSED |
| 4 | Workspace Integration | 🟢 PASSED |
| 5 | Fail-Closed Critic Stress Test (12/12 adversarial attacks defeated) | 🟢 PASSED |
| 6 | Developer Journey E2E (Understand → Ask → Debug → Build → Review → Wiki) | 🟢 PASSED |
| 7 | Automated Regression Suite (all test suites passing) | 🟢 PASSED |
| 8 | Multi-Container Docker Stack | 🟢 PASSED |
| 9 | Runtime Security Audit (Zip Slip, Path Traversal, JWT, LLM fallback) | 🟢 PASSED |
| 10 | P3 CodeTurtle Review Intelligence (53/53 Review/OCR tests, 69/69 Unit, 20/20 Wiki) | 🟢 PASSED |

---

## 18. Current Platform Completion Roadmap

```
PHASE 0 — PLATFORM FOUNDATION (✅ COMPLETED)
──────────────────────────────────────────────
AST → KuzuDB → FAISS → Repository Brain → Critic → Security → Docker → Staging

PHASE 1 — POLYGLOT EXPANSION (✅ COMPLETED)
─────────────────────────────────────────────
Tree-sitter URM → Python Adapter → TypeScript Adapter → Go Adapter
→ Rust Adapter → C# Adapter → C++ Adapter → 21 languages supported

PHASE 2 — REPOSITORY-FIRST ARCHITECTURE (✅ COMPLETED)
───────────────────────────────────────────────────────
DeepWiki (wiki.py + wiki_depth.py) → Component Inspector → Change Impact
→ Debug Center → Session Memory → 11-Workspace Navigation Layout

PHASE 3 — CODETURTLE REVIEW INTELLIGENCE (✅ COMPLETED)
────────────────────────────────────────────────────────
1. P3-A: OpenCodeReview (Apache-2.0) Architecture & License Audit (Native Implementation)
2. P3-B / P3-E: RuleSniffer & Pre-Verifier Negative Constraints:
   - Expanded catalog to 12+ languages: Java, Python, TS/JS, Go, Rust, C/C++, Kotlin, Swift, SQL, Dockerfile, CI/CD YAML
   - Rule Engine = Review Intelligence, ClaimVerifier = Truth Boundary
3. P3-C: Hunk-based Line Relocation & Cross-File Line Resolver (Ambiguous matches fail closed)
4. P3-D: Myers Line-Diff Engine (Shortest edit scripts, 1-click committable explicit user patches)
5. P3-E: Comment Args Serialization Repair Engine (devlensx/review/repair.py):
   - Escapes prose quotes, raw control chars, illegal backslashes; truncations fail closed
6. P3-F: Smart File Grouping & Token Budgeting Engine (devlensx/review/chunking.py):
   - Churn calculation, token estimation, and semantic file bundling to avoid context blowout
7. P3-G: End-to-End Review Pipeline:
   - Diff → RuleSniffer → Chunking → LLM Reasoning → Serialization Repair → Pre-Filter → Relocation → ClaimVerifier → SuggestDiff → UI
8. P3-H: Full Workspace Mirroring:
   - Primary active workspace at d:/projects/DevLensX kept 100% in sync with Desktop; clean frontend build and 71 review tests passing.

PHASE 4 — ENTERPRISE & PUBLISHING (PLANNED)
────────────────────────────────────────────
1. Multi-repo workspace support
2. CI/CD integration (GitHub Actions PR Review Bot)
3. MCP IDE plugin (VS Code / JetBrains)
4. Academic paper submission (IEEE ICPC / SANER 2027)
```
