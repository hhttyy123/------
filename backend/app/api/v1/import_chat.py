"""Import diagnosis chat API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.import_chat import ask_import_question

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ImportChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


@router.post("/import/batches/{batch_id}/chat")
async def chat_with_import_batch(batch_id: str, req: ImportChatRequest):
    try:
        return await ask_import_question(
            batch_id=batch_id,
            question=req.question,
            history=[message.model_dump() for message in req.history],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("import chat failed")
        raise HTTPException(status_code=500, detail=f"诊断失败: {exc}")
