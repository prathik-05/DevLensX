# DevLensX — Evidence-Grounded Repository Intelligence Platform

> **DevLensX — Understand, Debug, Build, and Review Any Codebase with Evidence.**  
> *A production-ready software intelligence platform combining a Universal Repository Model (URM), embedded property graphs, dense semantic search, and hybrid GraphRAG retrieval with fail-closed ClaimVerifier verification.*

---

## 🚀 Executive Summary & Core Identity

DevLensX is an evidence-verified codebase intelligence workspace designed for modern software engineering teams. Traditional AI coding tools operate statelessly over isolated file snippets and frequently fabricate non-existent symbols, hallucinate dependencies, or misinterpret architectural boundaries.

DevLensX implements a **hybrid GraphRAG retrieval architecture** over a **Universal Repository Model (URM)**. Repository reasoning is separated into explicit, complementary layers that converge at a deterministic truth boundary:

```
                    ┌──────────────────────────────┐
                    │      Target Repository       │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Tree-sitter + Polyglot       │
                    │ Language Adapters            │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Universal Repository         │
                    │ Model (URM)                  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Repository Knowledge         │
                    │ Graph                        │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      GraphRAG Layer          │
                    └──────────────┬───────────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
      ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
      │ Kùzu Graph  │       │    FAISS    │       │  Evidence   │
      │  Structural │       │   Semantic  │       │    Store    │
      │  Retrieval  │       │  Retrieval  │       │  Grounding  │
      └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   ClaimVerifier Boundary     │
                    │ (AST Grounding & EvidenceRef)│
                    └──────────────┬───────────────┘
                                   │
         ┌───────────────┬─────────┼─────────┬───────────────┐
         ▼               ▼         ▼         ▼               ▼
      RepoMind       Assistant CodeTurtle  Change       Build Studio
     Living Wiki       Chat      Review    Impact         & Debug
         │               │         │         │               │
         └───────────────┴─────────┼─────────┴───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Developer Workspace          │
                    └──────────────────────────────┘
```

### The Architecture of Knowledge: URM → Graph → GraphRAG

DevLensX strictly avoids blurring the boundaries between data models, storage engines, retrieval architectures, and verification gates:

- **Universal Repository Model (URM)**: *"What entities and relationships exist in this codebase?"* — Canonical in-memory AST model normalizing classes, methods, fields, and imports across Java, TypeScript, JavaScript, and Python.
- **Repository Knowledge Graph**: *"What is the relational ontology of the system?"* — Conceptual property graph of `DEPENDS_ON`, `CALLS`, `INHERITS_FROM`, and `EXPOSES_API` relationships.
- **Kùzu Graph Engine**: *"What is structurally related to this symbol/module/file?"* — High-performance embedded C++ graph storage executing Cypher queries for deep call graph and blast-radius exploration.
- **FAISS Vector Index**: *"What repository content is semantically relevant to this question?"* — Dense vector search over symbol docstrings, intents, and comments.
- **Evidence Store / SourceReader**: *"Where exactly in the source can this claim be grounded?"* — Deterministic line-level source reader anchoring claims to exact lines (`[file#Lstart-Lend]`).
- **GraphRAG Retrieval Layer**: *"How should these different forms of repository context be combined for the reasoning task?"* — Hybrid retrieval coordinating structural graph traversal, semantic search, and deterministic excerpts.
- **ClaimVerifier**: *"Does the resulting claim actually meet DevLensX's verification requirements?"* — Truth boundary enforcing the frozen Claim Taxonomy (`VERIFIED`, `AI_SUGGESTION`, `INSUFFICIENT`).

---

## 📦 Modular Backend Architecture (`devlensx/`)

```
devlensx/
├── api/
│   ├── routes/
│   │   ├── auth.py          # /api/auth/register, /api/auth/login, /api/auth/me
│   │   └── repositories.py  # /api/repositories CRUD & analyze routes
│   └── main.py              # Central FastAPI server definition & router registration
├── core/
│   ├── config.py            # Platform configurations & score weights
│   └── security.py          # PBKDF2 HMAC password hashing & JWT token processing
├── db/
│   ├── database.py          # SQLite database connection & table initialization
│   └── models.py            # Relational models (User, Repository, AnalysisRun, Finding)
├── schemas/
│   ├── auth.py              # User & JWT Pydantic schemas
│   ├── repository.py        # Repository & Analyze request schemas
│   └── copilot.py           # Copilot, Debug & PR Review schemas
├── services/
│   ├── auth_service.py      # Registration & authentication business logic
│   ├── repository_service.py# Repository management & file validation
│   ├── analysis_service.py  # Ingestion & 5-stage pipeline runner
│   ├── copilot_service.py   # Context resolution & LLM response processing
│   └── git_service.py       # Git commit churn facts & stack trace debugging
├── parser/                  # Javalang AST parsing engine
├── graph/                   # KuzuDB embedded C++ property graph store
├── retrieval/               # GraphRAG (FAISS + 2-hop Cypher traversal)
├── critic/                  # Fail-Closed Critic Grounding Engine
└── llm/                     # Unified LLM provider drivers (Gemini, OpenAI, OpenRouter)
```

---

## 💻 Modular Frontend Architecture (`web/src/`)

```
web/src/
├── components/
│   ├── OverviewPage.tsx     # Goal-First Intent Cards & Senior Engineer Briefing
│   ├── ChangeImpactView.tsx # Build Studio 2.0 (Verified Zone vs. AI Suggestion Zone)
│   ├── CopilotPage.tsx      # DevLensX Assistant Chat View & Session Memory
│   ├── SecurityPage.tsx     # Security Vulnerabilities & PR Diff Impact
│   ├── ArchitecturePage.tsx # Constellation Knowledge Graph Visualizers
│   ├── DocsPage.tsx         # Living Documentation Generator
│   └── SettingsPage.tsx     # LLM Provider & API Key Configuration
├── App.tsx                  # React application shell & workspace router
├── apiClient.ts             # REST client with JWT headers & standalone fallbacks
└── types.ts                 # TypeScript interfaces
```

---

## 🛠️ Installation & Local Launch Protocol

### 1. Environment Setup (`.env`)
Create a `.env` file in the project root:
```ini
DATABASE_URL=sqlite:///./devlensx.db
JWT_SECRET=devlensx_production_secret_key_987654321

# Unified LLM Provider Keys (Provide AT LEAST ONE key below)
LLM_PROVIDER=auto
GEMINI_API_KEY=AIzaSy_YOUR_GEMINI_API_KEY_HERE
# OR
OPENROUTER_API_KEY=sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE
```

### 2. Launch Local Development
```bash
# Terminal 1: Launch FastAPI REST Server
python run_devlensx.py api

# Terminal 2: Launch React Web Platform UI
python run_devlensx.py web
```

- **Web Workspace UI:** `http://localhost:5173`
- **FastAPI REST Server:** `http://127.0.0.1:8000`

---

## 📊 Ground-Truth Benchmark Results

Tested against locked benchmark evaluation datasets (`eval_dataset_spring-petclinic.json`, `eval_dataset_mybatis-3.json`, `eval_dataset_dubbo.json`):

- **Pooled Dataset Size (N):** 73 Stratified Findings
- **Pre-Fix vs. Post-Fix Verdict Match:** **72 / 73 (98.6%)**
- **Ground-Truth True Positive False Rejection Rate (FRR):** **0.0% (0/29 TPs rejected)**.

---

## 🐳 Docker Deployment

Run multi-container production stack via Docker Compose:
```bash
docker-compose up --build
```
