# Route Inventory & Navigation Map — DevLensX

> **Complete Mapping of Frontend Views and Backend REST API Endpoints**

---

## 1. Backend REST API Endpoints (`devlensx/api/main.py`)

All backend endpoints are served via FastAPI on `http://127.0.0.1:8000`.

| Method | Endpoint Route | Request Body / Parameters | Description & Responsibility | Auth / Gate |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | None | Root status check returning platform identity. | Public |
| `POST` | `/api/analyze` | `AnalyzeRequest` (`repo_path`, `source`, `inject_hallucination`) | Runs full 5-stage pipeline: parse AST, build KuzuDB graph, run agents, Critic verification, synthesize score. | Public |
| `GET` | `/api/score` | None | Retrieves latest Repository Intelligence Score & sub-scores. | Public |
| `POST` | `/api/retrieval` | `RetrievalRequest` (`query`, `top_k_graph`, `top_k_vector`) | Executes Hybrid GraphRAG retrieval (Cypher triples + FAISS embeddings). | Public |
| `POST` | `/api/copilot/ask` | `CopilotAskRequest` (`question`, `session_history`, `provider`, `api_key`) | DevLensX Assistant Q&A endpoint. Resolves context across session history turns. | Public |
| `POST` | `/api/copilot/decision` | `EngineeringDecisionRequest` (`decision_query`, `target_component`) | Evaluates architectural trade-offs with repository evidence. | Public |
| `POST` | `/api/planner/classify` | `PlannerClassifyRequest` (`question`) | Classifies user question intent into architectural categories. | Public |
| `GET` | `/api/change-impact/{class_name}` | Path param: `class_name` (string) | Calculates transitive downstream blast radius for a given target class. | Public |
| `POST` | `/api/reviews/pr-review` | `PRReviewRequest` (`diff`, `custom_prompt`, `repo_id`) | Audits pull request diffs against parsed repository memory. | Public |
| `GET` | `/api/features/clusters` | None | Groups classes into Business Feature Boundaries via package + graph community detection. | Public |
| `GET` | `/api/git/churn` | None | Runs `git log --follow` per component file to extract checkable commit facts and fix keywords. | Public |
| `POST` | `/api/debug/trace` | `TraceDebugRequest` (`stack_trace`) | Maps class & method tokens from user-pasted stack traces against parsed AST graph nodes. | Public |

---

## 2. Frontend Application Navigation Routes (`web/src/`)

Frontend state navigation managed in `web/src/App.tsx` via `TabType` state union:

| Tab Identifier | View Component | Primary Purpose & Features | Navigation Trigger |
| :--- | :--- | :--- | :--- |
| `'learn'` / `'overview'` | [`OverviewPage.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/OverviewPage.tsx) | Goal-First primary workspace. Renders 6 intent cards, Senior Engineer Briefings, business request execution flows, and togglable Technical Engine drawer. | Sidebar "Overview" or Brand Logo |
| `'copilot'` | [`CopilotPage.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/CopilotPage.tsx) | DevLensX Assistant chat view. Provides grounded answers, evidence drawers, and follow-up prompts. | Sidebar "Ask DevLensX" |
| `'build'` | [`ChangeImpactView.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/ChangeImpactView.tsx) | Build Studio 2.0 Feature Planner. Generates feature plans with strict separation between VERIFIED ZONE (Graph Facts) and SUGGESTION ZONE (AI Proposals). | Sidebar "Build Studio" |
| `'reviews'` | [`SecurityPage.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/SecurityPage.tsx) | PR Review & Security Vulnerability audit interface. Shows unauthenticated endpoints, hardcoded credentials, and PR diff impact. | Sidebar "PR & Security" |
| `'architecture'` | [`ArchitecturePage.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/ArchitecturePage.tsx) | Interactive Knowledge Graph visualizer (`GalaxyConstellationGraph.tsx` & `KnowledgeGraphView.tsx`). | Header "Technical Engine View" / Sidebar "Architecture" |
| `'docs'` | [`DocsPage.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/DocsPage.tsx) | Automated living documentation generator (READMEs, Architecture Guides, Day-1 Onboarding Roadmaps). | Sidebar "Documentation" |
| `'settings'` | [`SettingsPage.tsx`](file:///C:/Users/SVCS/Desktop/DevLensX/web/src/components/SettingsPage.tsx) | LLM Provider selection (Gemini, OpenAI, OpenRouter) and API Key management. | Sidebar "Settings" |
