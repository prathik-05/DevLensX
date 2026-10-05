# Supported Languages

**Generated from `POLYGLOT_VALIDATION_MATRIX.json` via `python -m devlensx.polyglot.matrix`**

| Language | Tree-sitter Parser | Adapter | Real Repository | Validation | Status |
|----------|-------------------|---------|-----------------|------------|--------|
| Java | Yes | Yes | spring-petclinic | URM→Kuzu→FAISS→Wiki→Evidence→Diagrams→Chat→Workspace | 🟢 VALIDATED |
| TypeScript | Yes | Yes | sp-portfolio | same pipeline | 🟢 VALIDATED |
| Python | Yes | Yes | battleship-python | same pipeline | 🟢 VALIDATED |
| JavaScript | Yes | Yes | — | — | ⏳ VALIDATION_PENDING |
| Go | Yes | Available/pending | — | — | ⏳ VALIDATION_PENDING |
| Rust | Yes | Available/pending | — | — | ⏳ VALIDATION_PENDING |
| C# | Yes | Available/pending | — | — | ⏳ VALIDATION_PENDING |
| C++ | Yes | Available/pending | — | — | ⏳ VALIDATION_PENDING |

**Definitions:**
- **PARSER_AVAILABLE**: Tree-sitter grammar loads
- **ADAPTER_AVAILABLE**: `devlensx/urm/adapters/<lang>_adapter.py` exists
- **VALIDATED**: Real repository passed discovery→parse→URM→Kuzu→FAISS→Brain→Wiki→Evidence→Diagrams→Chat→Workspace with snapshot isolation
- **VALIDATION_PENDING**: Grammar/adapter may exist but no real-repo end-to-end evidence
- **UNSUPPORTED**: Language detected → `⚪ UNSUPPORTED LANGUAGE` status, no fake claims
