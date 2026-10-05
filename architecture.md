# Pipeline & System Architecture — DevLensX

> **Detailed Architecture Specification for DevLensX Engine & Web Platform**

---

## 1. System Pipeline Overview

DevLensX operates on a deterministic, evidence-verified intelligence pipeline. Unlike pure LLM-based assistants that guess repository structures, DevLensX uses AST parsing and embedded property graphs to establish a verified ground-truth knowledge base before generating natural language answers.

```
+-----------------------------------------------------------------------------------+
|                                  INPUT REPOSITORY                                 |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| STAGE 1: AST PARSER ENGINE (devlensx/parser/java_parser.py)                       |
| - Extracts class names, packages, stereotypes (Controller, Service, Repo, Entity) |
| - Extracts fields, methods, parameters, annotations (@RestController, @GetMapping)|
| - Identifies injected dependencies (@Autowired, constructor injection)            |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| STAGE 2: KUZUDB GRAPH STORE (devlensx/graph/kuzu_store.py)                        |
| - Embedded Graph Database stored in .devlensx-runtime/                            |
| - Nodes: JavaClass (name, stereotype, package, file)                              |
| - Edges: DEPENDS_ON, EXTENDS, IMPLEMENTS                                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| STAGE 3: MULTI-AGENT ANALYZER SUITE (devlensx/agents/)                            |
| - ArchitectureAgent: Detects god classes, tight coupling, circular dependencies  |
| - SecurityAgent: Detects unauthenticated APIs, hardcoded credentials, secret leaks|
| - ChangeImpactAgent: Computes transitive caller impact & blast-radius counts     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| STAGE 4: FAIL-CLOSED CRITIC GROUNDING LAYER (devlensx/critic/critic_engine.py)    |
| - Evaluates findings across 4 evidence channels: Graph, AST, Semgrep, Structure   |
| - Enforces method count equality (actual_methods >= claimed_methods)              |
| - Fails closed if target fields or endpoints are missing in AST                   |
| - Rejects findings with evidence score < 50.0%                                    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| STAGE 5: UNIFIED LLM & RECOMMENDATION ENGINE (devlensx/llm/ & recommendation/)    |
| - GeminiProvider / OpenAIProvider / OpenRouterProvider drivers                    |
| - Computes Overall Repository Intelligence Score & sub-scores                    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| STAGE 6: GOAL-FIRST DEVELOPER WORKSPACE (web/src/components/)                     |
| - Goal Palette: Understand, Debug, Build Studio, PR Review, Security, Docs        |
| - Strict visual separation: VERIFIED ZONE vs. SUGGESTION ZONE                     |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Subsystem Responsibilities

### A. Parser Engine (`devlensx/parser/`)
- `java_parser.py`: Uses `javalang` AST trees to parse Java source files. Extracts class stereotypes (`Controller`, `Service`, `Repository`, `Entity`, `Configuration`, `Test`), fields, methods, parameters, annotations, and injected dependencies.
- `regex_parser.py`: Non-Java regex fallback parser (gated by pre-flight checks).

### B. Knowledge Graph Engine (`devlensx/graph/`)
- `kuzu_store.py`: Embedded C++-powered property graph engine. Executes Cypher queries over `JavaClass` nodes and relational edges (`DEPENDS_ON`, `EXTENDS`, `IMPLEMENTS`). Provides fast graph traversal without external server overhead.
- `neo4j_store.py`: Alternative remote Neo4j connector.

### C. Hybrid Retrieval Engine (`devlensx/retrieval/`)
- `faiss_retriever.py`: Builds a 384-dimensional vector embedding space over class documentation and signatures using FAISS.
- `hybrid_retriever.py`: Combines 2-hop Cypher graph traversal with FAISS vector similarity to provide GraphRAG retrieval context.

### D. Multi-Agent Analyzer Suite (`devlensx/agents/`)
- `architecture_agent.py`: Identifies god-classes (incoming dependencies >= 5) and high-coupling risks.
- `security_agent.py`: Identifies unauthenticated REST endpoints and potential SQL/secret vulnerabilities.
- `change_impact_agent.py`: Performs reverse dependency traversal to calculate blast-radius call chains when a component changes.

### E. Fail-Closed Critic Grounding Engine (`devlensx/critic/`)
- `critic_engine.py`: Acts as the quality gate. Every agent finding must pass empirical verification:
  - **Graph Check:** Verifies node presence and edge relationship in KuzuDB.
  - **AST Check:** Verifies exact field names, setter parameters, or REST endpoint paths in AST.
  - **Structural Check:** Verifies file path existence on disk (with OS path normalization).
  - **Semgrep Check:** Validates security rule matches.
- Findings scoring >= 50.0% are marked `VERIFIED`. All others are `REJECTED`.

### F. Unified LLM Abstraction Layer (`devlensx/llm/`)
- `provider.py`: Defines standard `LLMProvider` interface and drivers:
  - `GeminiProvider`: Google Gemini 1.5 Flash API
  - `OpenAIProvider`: OpenAI GPT-4o / GPT-4o-mini API
  - `OpenRouterProvider`: OpenRouter unified API
- Intersects with `/api/copilot/ask` for natural language query generation.

---

## 3. Frontend Architecture (`web/src/`)

- **State Container (`App.tsx`):** Manages active workspace repository, selected navigation tab (`learn`, `copilot`, `build`, `reviews`, `architecture`, `security`, `docs`, `settings`), and global analysis response payload (`AnalysisResponse`).
- **Goal-First Palette (`OverviewPage.tsx`):** Renders intent cards, Senior Engineer Briefings, business request execution flows (`HTTP Request → Controller → Repository → DB`), and togglable **Technical Engine View** drawer.
- **Build Studio 2.0 (`ChangeImpactView.tsx`):** Interactive feature planner enforcing strict separation between **VERIFIED ZONE (Graph Facts)** and **SUGGESTION ZONE (AI Proposals)**.
- **REST Client (`apiClient.ts`):** Handles HTTP communication with the FastAPI backend at `http://127.0.0.1:8000` with graceful offline fallback mocking.

---

## 4. Native GitIngest Engine & Repo Context Ingest (`devlensx/ingest.py`)

DevLensX provides a native GitIngest-style engine that bundles any GitHub repository or local directory into a prompt-ready LLM digest without shelling out to external services.

- **SSRF Protection & URL Parsing**: Validates that all remote repository URLs strictly belong to `github.com`. Automatically parses repository branches, subpaths, and `.git` suffixes while guarding against path traversal attacks.
- **Clone Engine**: Performs single-branch shallow clones (`--depth 1`) inside managed temporary directories with a 60s timeout, repository size guard, and token support for private repositories (with tokens masked in all logs and outputs).
- **Filtering & Skipping**: Reuses the repository exclusion policies (`devlensx/repository.py`), discarding `.git`, `node_modules`, `venv`, binary files (8KB null-byte sniffing), lockfiles, minified files, source maps, and media. Supports user-specified `include_patterns` and `exclude_patterns` using `.gitignore`-compatible `pathspec` matchers.
- **LLM Context Digest Output (`IngestResult`)**:
  - `summary`: Metadata including repository name, branch, commit SHA, file count, total bytes, and token count estimated via `tiktoken` (`cl100k_base` with heuristic fallback).
  - `tree`: Formatted ASCII directory hierarchy tree.
  - `files`: File list with relative path, size, language detection, and content.
  - `digest`: Standardized LLM prompt digest with `FILE: <path>` separators and automated 300k-character preview truncation.
- **Direct Pipeline Bridge (`/api/analyze/from-ingest`)**: Enables instant hand-off of ingested repositories straight into `Pipeline.analyze()` without cloning twice.
- **Interactive UI (`IngestView.tsx`)**: Dark-glass UI providing live token recomputation upon checkbox selection in a collapsible directory tree, preview pane, copy/download actions, and single-click DevLensX analysis trigger.

