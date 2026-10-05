# Architecture

## Overview
Repository → Tree-sitter + Adapters → URM → RepositoryBrain (Kuzu+FAISS+Evidence+ClaimVerifier) → Wiki/Diagrams/Chat/Workspace

## D1 Parsing
Tree-sitter grammars + language adapters (java, python, typescript, javascript, go, rust, csharp, cpp) produce symbols with SourceLocation (file, line_start/end) and relationships (IMPORTS, CALLS, DEPENDS_ON, EXTENDS, IMPLEMENTS). Adapters registered in `devlensx/urm/adapters/`.

## D2 URM
Unified Repository Model: Repository { Files, Symbols, Relationships, Endpoints, Configurations, SourceLocations }. Single IR for downstream.

## D3 Execution
Discovery → parse → URM → Kuzu (graph) → FAISS (vectors) → RepositoryBrain. Validated on spring-petclinic (Java 49 files/435 symbols), sp-portfolio (TS 59/98), battleship-python (Python 5/25).

## RepositoryBrain
`devlensx/understanding/model/repository_brain.py` holds URM + Kuzu + FAISS + Evidence + ClaimVerifier. Trust hierarchy: AST/URM/Kuzu/D5/D6 = proof; FAISS = context only; LLM → candidate → ClaimVerifier → VERIFIED/AI_SUGGESTION/INSUFFICIENT.

## D4-D9
- **D4 Planner**: DocumentationTree from RepositoryBrain → EvidenceScope
- **D5 Evidence**: EvidenceRef(repository_id+run_id+commit+file+lines+symbol) → SourceReader (1 MB, binary, symlink, traversal safe) → Resolver (UNKNOWN_SNAPSHOT/PATH_VIOLATION/STALE_COMMIT)
- **D6 Diagrams**: DEPENDENCY/ARCHITECTURE/COMPONENT/CALL_GRAPH/DATA_FLOW/SEQUENCE → JSON → InteractiveDiagram + Mermaid
- **D7 Wiki**: PageGenerator → ClaimExtractor → ClaimVerifier → VerifiedDocPage (VERIFIED/SUGGESTION/INSUFFICIENT)
- **D8 Chat**: FAST/CODEMAP/DEEP_RESEARCH → ChatOrchestrator → VerifiedAnswer with evidence_refs, snapshot-bound
- **D9 Workspace**: WorkspaceContext + Session + Impact/Build/Debug/Review → all snapshot-bound, no second graph/FAISS/Brain

## D10 Hardening
- **D10.1**: Isolated E2E (temp Kuzu, ports, SnapshotRegistry)
- **D10.2**: Security (Zip Slip, traversal, command injection list-based, prompt injection as data, secret redaction)
- **D10.3**: Incremental (git diff → symbols → Kuzu impact → invalidation → new snapshot, old immutable)
- **D10.4**: Performance baselines via `devlensx/performance`
- **D10.5**: Polyglot matrix `POLYGLOT_VALIDATION_MATRIX.json`
- **D10.6**: Golden 33 cases
- **D10.7**: Status model + UX states
- **D10.8**: Observability (Event/Metric/Health + redaction + X-Request-ID)
