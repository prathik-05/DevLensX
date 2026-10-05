# Dependency Graph & Core Component Impact — DevLensX

> **Python Module Import Hierarchy, Critical System Files, and Modification Safety Rules**

---

## 1. Module Import Dependency Hierarchy

```
                                    run_devlensx.py (CLI Entry Point)
                                                   │
                                                   ▼
                                     devlensx/api/main.py (FastAPI Server)
                                                   │
                ┌──────────────────────────────────┼──────────────────────────────────┐
                │                                  │                                  │
                ▼                                  ▼                                  ▼
devlensx/repository_memory/        devlensx/critic/                    devlensx/llm/
(MemoryEngine)                     (CriticAgent / Engine)              (LLMProvider Abstraction)
                │                                  │                                  │
      ┌─────────┴─────────┐                        │                                  │
      ▼                   ▼                        │                                  │
devlensx/parser/   devlensx/graph/                 │                                  │
(JavaASTParser)    (KuzuGraphStore)                │                                  │
      │                   │                        │                                  │
      └─────────┬─────────┘                        │                                  │
                ▼                                  ▼                                  ▼
devlensx/retrieval/                devlensx/agents/                    devlensx/recommendation/
(HybridRetriever)                  (ArchitectureAgent,                 (RecommendationEngine)
                                    SecurityAgent,
                                    ChangeImpactAgent)
```

---

## 2. Critical Core Files (High Impact — Do Not Modify Lightly)

The following files constitute the structural backbone of DevLensX. Any edits to these files carry high risk:

| File Path | Core Responsibility | Why It Is Critical | Modification Risk |
| :--- | :--- | :--- | :--- |
| [`devlensx/critic/critic_engine.py`](file:///C:/Users/SVCS/Desktop/DevLensX/devlensx/critic/critic_engine.py) | Fail-Closed Critic Verification Engine | Enforces method count equality, path normalization, and AST field/endpoint checks. Ensures **0.0% False Rejection Rate**. | **CRITICAL:** Relaxing checks introduces hallucinated findings. |
| [`devlensx/parser/java_parser.py`](file:///C:/Users/SVCS/Desktop/DevLensX/devlensx/parser/java_parser.py) | Javalang AST Parsing Engine | Extracts class stereotypes, methods, fields, annotations, and injected dependencies from Java codebases. | **HIGH:** Parser bugs cause missing graph nodes or broken edges. |
| [`devlensx/graph/kuzu_store.py`](file:///C:/Users/SVCS/Desktop/DevLensX/devlensx/graph/kuzu_store.py) | KuzuDB Property Graph Store | Manages embedded C++ graph storage, Cypher queries, and node/edge insertions. | **HIGH:** Schema edits require updating all Cypher query strings. |
| [`devlensx/llm/provider.py`](file:///C:/Users/SVCS/Desktop/DevLensX/devlensx/llm/provider.py) | Unified LLM Provider Drivers | Handles API requests to Gemini, OpenAI, and OpenRouter. | **MEDIUM:** Ensure fallback error handling stays intact. |
| [`devlensx/api/main.py`](file:///C:/Users/SVCS/Desktop/DevLensX/devlensx/api/main.py) | FastAPI REST Router & Endpoints | Exposes all 12 REST endpoints and manages global state objects. | **HIGH:** Route edits break frontend `apiClient.ts` integration. |
| [`web/src/App.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/App.tsx) | React Application Shell & Router | Manages tab state, workspace analysis state, and global layouts. | **MEDIUM:** State edits impact all tab components. |
| [`web/src/components/ChangeImpactView.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/ChangeImpactView.tsx) | Build Studio 2.0 Feature Planner | Renders verified graph impact alongside AI suggested implementation proposals. | **MEDIUM:** Preserve separation of VERIFIED vs. SUGGESTION zones. |

---

## 3. Package Dependencies (`requirements.txt` & `package.json`)

### Python Core Dependencies
- `javalang` (0.13.0+): AST parser for Java.
- `kuzu` (0.4.0+): Embedded C++ property graph.
- `neo4j` (5.14.0+): Remote graph database fallback driver.
- `faiss-cpu` (1.7.4+): Dense vector indexing for GraphRAG.
- `fastapi` (0.104.0+) & `uvicorn` (0.23.2+): REST API framework.

### Frontend Dependencies (`web/package.json`)
- `react` (18.3.1) & `react-dom` (18.3.1): Frontend SPA library.
- `lucide-react` (0.469.0): Icon library.
- `tailwindcss` (3.4.17): Utility-first CSS styling framework.
- `vite` (6.0.5): Production asset bundler and dev server.
