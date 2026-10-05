"""
DevLensX Chat API Routes (D8)

POST /api/chat/{analysis_run_id}
POST /api/chat/{analysis_run_id}/stream  (SSE)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from devlensx.chat.orchestrator import ChatOrchestrator

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatAskRequest(BaseModel):
    message: str = Field(min_length=1)
    mode: str = Field(default="FAST")
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, str]]] = None


@router.post("/{analysis_run_id}")
def chat_ask(analysis_run_id: str, req: ChatAskRequest):
    try:
        ans = ChatOrchestrator.chat(
            analysis_run_id=analysis_run_id,
            message=req.message,
            mode=req.mode,
            context=req.context,
        )
        return ans.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{analysis_run_id}/stream")
def chat_stream(analysis_run_id: str, req: ChatAskRequest):
    try:
        gen = ChatOrchestrator.stream(
            analysis_run_id=analysis_run_id,
            message=req.message,
            mode=req.mode,
            context=req.context,
        )
        return StreamingResponse(gen, media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))