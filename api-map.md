# REST API Map & Data Contracts — DevLensX Engine

> **Comprehensive Inventory of FastAPI REST Endpoints, Input Models, and Output Schemas**

---

## API Inventory & Data Contracts

### 1. Repository Analysis (`POST /api/analyze`)
* **File:** `devlensx/api/main.py`
* **Input Request Model (`AnalyzeRequest`):**
  ```json
  {
    "repo_path": "eval_repos/spring-petclinic",
    "source": "",
    "inject_hallucination": false
  }
  ```
* **Output Response (`AnalysisResponse`):**
  ```json
  {
    "status": "success",
    "repository": "spring-petclinic",
    "repo_summary": {
      "language": "Java",
      "controllers": 4,
      "services": 3,
      "repositories": 2,
      "entities": 6,
      "rest_apis": 12,
      "total_classes": 24
    },
    "parse_stats": { "files_parsed": 24, "classes_found": 24, "endpoints_found": 12 },
    "graph_edge_stats": { "DEPENDS_ON": 15, "EXTENDS": 4, "IMPLEMENTS": 6 },
    "timing_metrics": {
      "parse_ast_ms": 25.4,
      "graph_build_ms": 120.1,
      "multi_agent_scan_ms": 85.0,
      "critic_grounding_verification_ms": 45.0,
      "recommendation_synthesis_ms": 10.0,
      "total_execution_ms": 285.5
    },
    "repository_intelligence_score": {
      "overall": 94.5,
      "sub_scores": {
        "architecture": 96.0,
        "security": 92.0,
        "maintainability": 95.0,
        "coupling": 94.0,
        "evidence_coverage": 98.0
      }
    },
    "top_engineering_recommendations": [],
    "classes": []
  }
  ```
* **Used By:** `web/src/App.tsx`, `run_devlensx.py analyze`

---

### 2. DevLensX Assistant Q&A (`POST /api/copilot/ask`)
* **File:** `devlensx/api/main.py`
* **Input Request Model (`CopilotAskRequest`):**
  ```json
  {
    "question": "Where is JWT validated?",
    "session_history": [
      { "role": "user", "content": "Explain authentication" },
      { "role": "assistant", "content": "Authentication is handled by SecurityConfig and JwtFilter..." }
    ],
    "provider": "gemini",
    "api_key": "private_key_string"
  }
  ```
* **Output Response:**
  ```json
  {
    "plain_english": "JWT validation takes place inside JwtAuthenticationFilter#doFilterInternal...",
    "recommendation": "Inspect SecurityConfig authorization rules to ensure JWT filter is registered before UsernamePasswordAuthenticationFilter.",
    "impact": {
      "directly_affected": 2,
      "potentially_affected": 4,
      "affected_names": ["SecurityConfig", "JwtAuthenticationFilter"]
    },
    "evidence": {
      "graph": true,
      "ast": true,
      "semgrep": true,
      "structure": true,
      "sources": ["KuzuDB Graph Engine", "AST Index"]
    },
    "follow_up_suggestions": [
      "Show SecurityConfig authorization rules",
      "Trace authentication execution flow"
    ]
  }
  ```
* **Used By:** `web/src/components/CopilotPage.tsx`, `web/src/components/AssistantView.tsx`

---

### 3. Change Impact Blast Radius (`GET /api/change-impact/{class_name}`)
* **File:** `devlensx/api/main.py`
* **Path Parameter:** `class_name` (e.g. `OwnerRepository`)
* **Output Response (`ChangeImpactResult`):**
  ```json
  {
    "target_class": "OwnerRepository",
    "risk_level": "HIGH",
    "total_affected_count": 3,
    "affected_classes": [
      { "class_name": "OwnerController", "stereotype": "Controller", "file": "OwnerController.java" }
    ],
    "affected_controllers": [
      { "class_name": "OwnerController", "stereotype": "Controller" }
    ],
    "affected_services": [],
    "affected_tests": [{ "class_name": "ClinicServiceTests" }]
  }
  ```
* **Used By:** `web/src/components/ChangeImpactView.tsx`

---

### 4. Feature Memory Clusters (`GET /api/features/clusters`)
* **File:** `devlensx/api/main.py`
* **Output Response:**
  ```json
  {
    "status": "success",
    "feature_clusters": [
      {
        "feature": "Owner",
        "class_count": 4,
        "classes": ["OwnerController", "OwnerService", "OwnerRepository", "Owner"],
        "boundary_status": "🟢 DETERMINISTIC GRAPH CLUSTER"
      }
    ]
  }
  ```
* **Used By:** `web/src/components/OverviewPage.tsx`, `web/src/components/ChangeImpactView.tsx`

---

### 5. Honest Git Churn Facts (`GET /api/git/churn`)
* **File:** `devlensx/api/main.py`
* **Output Response:**
  ```json
  {
    "status": "success",
    "churn_data": [
      {
        "file": "src/main/java/com/example/demo/system/WelcomeController.java",
        "class_name": "WelcomeController",
        "commit_count": 12,
        "fix_commit_heuristic_count": 2,
        "label": "Fact (Checkable via git log)",
        "heuristic_note": "2 commits contain 'fix/bug' keywords in message"
      }
    ]
  }
  ```
* **Used By:** `web/src/components/OverviewPage.tsx`, `web/src/components/SecurityPage.tsx`

---

### 6. Trace-Based Debugging (`POST /api/debug/trace`)
* **File:** `devlensx/api/main.py`
* **Input Request Model (`TraceDebugRequest`):**
  ```json
  {
    "stack_trace": "NullPointerException at com.example.demo.owner.OwnerController.processFindForm"
  }
  ```
* **Output Response:**
  ```json
  {
    "status": "success",
    "grounding_status": "🟢 GRAPH TRACE MAPPED",
    "matched_components": ["OwnerController"],
    "call_chain": ["OwnerController (Controller)"],
    "recommendation": "Grounding match: Stack trace references 1 parsed codebase class(es): OwnerController. Inspect call chain for potential null references."
  }
  ```
* **Used By:** `web/src/components/CopilotPage.tsx`, `web/src/components/OverviewPage.tsx`
