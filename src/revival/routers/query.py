from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from revival.models import QueryRequest
from revival.services.rag import query_stream

router = APIRouter(tags=["query"])


@router.post("/api/query")
async def query_documents(req: QueryRequest):
    return StreamingResponse(
        query_stream(req.question, history=req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
