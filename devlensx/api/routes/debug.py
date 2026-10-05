"""
DevLensX Stack Trace Debugger API Routes
"""

from fastapi import APIRouter
from devlensx.schemas.copilot import TraceDebugRequest
from devlensx.services.git_service import DebugService

router = APIRouter(prefix="/api/debug", tags=["Debugging"])


@router.post("/trace")
def trace_root_cause(req: TraceDebugRequest):
    """Maps class and method tokens in user-pasted stack traces against real parsed graph nodes."""
    from devlensx.api.main import global_state
    repo_model = global_state.get("repo_model") or {}
    classes = repo_model.get("classes", [])
    return DebugService.trace_stack_trace(req.stack_trace, classes)
