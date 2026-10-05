from enum import Enum
from typing import Optional, Dict, Any

class RepositoryStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    ANALYZING = "ANALYZING"
    INDEXING = "INDEXING"
    DOCUMENTING = "DOCUMENTING"
    READY = "READY"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    EMPTY = "EMPTY"
    STALE = "STALE"

class AnalysisStatus(str, Enum):
    ANALYZING = "ANALYZING"
    INDEXING = "INDEXING"
    GENERATING_WIKI = "GENERATING_WIKI"
    READY = "READY"
    FAILED = "FAILED"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    STALE_SNAPSHOT = "STALE_SNAPSHOT"
    NO_EVIDENCE = "NO_EVIDENCE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"

class ChatStatus(str, Enum):
    RETRIEVING = "RETRIEVING"
    VERIFYING = "VERIFYING"
    GENERATING = "GENERATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    STALE = "STALE"

class WorkspaceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    INVALID_SNAPSHOT = "INVALID_SNAPSHOT"
    FAILED = "FAILED"
    UNKNOWN_RUN = "UNKNOWN_RUN"
    REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
    STALE_COMMIT = "STALE_COMMIT"

def status_response(status: str, repository_id: Optional[str] = None, analysis_run_id: Optional[str] = None, commit_hash: Optional[str] = None, message: str = "", recoverable: bool = False, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = {
        "status": status,
        "repository_id": repository_id,
        "analysis_run_id": analysis_run_id,
        "commit_hash": commit_hash,
        "message": message,
        "recoverable": recoverable
    }
    if extra:
        resp.update(extra)
    # Never leak secrets
    for k in list(resp.keys()):
        if "api_key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
            resp[k] = "***"
    return resp

def error_response(status: str, message: str, repository_id=None, analysis_run_id=None, commit_hash=None, recoverable=True) -> Dict[str, Any]:
    return status_response(status, repository_id, analysis_run_id, commit_hash, message, recoverable)
