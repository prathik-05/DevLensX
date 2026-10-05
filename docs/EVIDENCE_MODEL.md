# Evidence Model
- `EvidenceRef(repository_id, analysis_run_id, commit_hash, file_path, line_start, line_end, symbol, evidence_type)`
- `SnapshotRecord` in `SnapshotRegistry` — immutable
- Verdicts: `VERIFIED` (EvidenceRef required), `AI_SUGGESTION` (explicit), `INSUFFICIENT_EVIDENCE` (no proving ref)
- Resolution: `UNKNOWN_SNAPSHOT`, `REPOSITORY_MISMATCH`, `STALE_COMMIT`, `PATH_VIOLATION`, `FILE_NOT_FOUND`, `BINARY_FILE`, `FILE_TOO_LARGE`, `INVALID_RANGE`, `RESOLVED`
- Snapshot isolation: filename alone never resolves; every artifact carries run_id+commit
