import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.models.dependencies import get_db, get_write_user, get_current_user
from app.core.database import User
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    conversation_id: str
    follow_up_questions: list[str] = []


class ConversationResponse(BaseModel):
    id: str
    title: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: list[str] = []
    created_at: str


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    try:
        result = RAGService.chat(
            db,
            current_user,
            request.question,
            request.document_id,
            request.conversation_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate answer")
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    def event_generator():
        try:
            for event in RAGService.chat_stream(
                db,
                current_user,
                request.question,
                request.document_id,
                request.conversation_id,
            ):
                yield _sse_event(json.loads(event))
        except ValueError as e:
            yield _sse_event({"type": "error", "detail": str(e)})
        except Exception:
            yield _sse_event({"type": "error", "detail": "Failed to generate answer"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convs = RAGService.list_conversations(db, current_user)
    return [
        ConversationResponse(
            id=str(c.id),
            title=c.title,
            updated_at=c.updated_at.isoformat() if c.updated_at else "",
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = RAGService.get_conversation_messages(db, current_user, conversation_id)
    return [
        MessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            sources=m.sources or [],
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    if not RAGService.delete_conversation(db, current_user, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}
