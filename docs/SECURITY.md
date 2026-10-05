# Security

## Threat Model
Repository code = UNTRUSTED DATA. Never becomes system instruction.

## Archive Security
- `is_safe_path` canonical check: realpath + commonpath, rejects `..`, `/etc/passwd`, `C:\Windows`, `\x00`, `%2e`/`%2f` double-encoding
- `POST /api/upload-zip`: MAX_ZIP_SIZE 100MB, MAX_EXTRACTED_FILES 10k, MAX_SINGLE 10MB, Zip Slip 403, BadZipFile 400
- No partial extraction on failure

## Path Traversal
- `SourceReader._safe_target`: rejects `..`, `/absolute`, `C:` drive, `\x00`, `lstrip` bypass, symlink escape via `relative_to(repo_root)`, empty/whitespace
- EvidenceRef requires `repository_id+run_id+commit+file+lines`; filename-only rejected (UNKNOWN_SNAPSHOT)

## Symlink / Binary / Size
- Symlink resolved + `relative_to` check → PATH_VIOLATION if escapes
- Binary sniff: `b\x00` or >30% non-text → BINARY_FILE
- 1 MB limit → FILE_TOO_LARGE, 400 lines window → INVALID_RANGE

## Command Injection
- All `git` calls list-based: `["git","log","--oneline","--", path]` — no `shell=True` with f-string
- Checked: `git_memory.py`, `git_service.py`, `java_parser.py` (subprocess list), `planner.py`

## Kuzu/Cypher
- Parameterized `prepare` + `execute({"tname": user_input})` — no `f"..." + user_input`

## Prompt Injection
- Context separation: SYSTEM | REPOSITORY EVIDENCE (URM/Kuzu/D5/D6) | USER QUERY
- Repository README/source comments with `IGNORE PREVIOUS INSTRUCTIONS` treated as data; claims about Redis/Kafka → `INSUFFICIENT_EVIDENCE` via ClaimVerifier

## Secrets
- Health returns `{"llm":"available"}` not raw keys; errors/logs redacted via `observability/redaction.py` (`OPENAI_API_KEY/Bearer/password` → `***REDACTED***`)
- SourceReader can read `.env` but Wiki/Chat do not auto-echo secrets; tests verify `FAKE_SECRET` not in health/logs/chat

## Resource Limits
- SourceReader 1 MB, Deep Research 6 subquestions/12 excerpts/20 files/3 hops, ZIP 100MB/10k, API 413 for huge payloads

## Build Safety
- `POST /api/workspace/{run}/build/plan` → ChangePlan (AI_SUGGESTION) only, verified hash before/after identical, no filesystem write

## Frontend XSS / Mermaid
- React auto-escapes; no raw `dangerouslySetInnerHTML` with repo text; Mermaid via `Diagram JSON → validated renderer → Mermaid/SVG`, `<script>` not in `mermaid_source`

## Snapshot / Workspace Isolation
- Every artifact `repository_id+run_id+commit`; `REPOSITORY_MISMATCH/STALE_COMMIT/UNKNOWN_RUN` enforced in Resolver, Workspace, Chat, Impact, Build, Debug, Review
