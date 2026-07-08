import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import ChatMessage, Conversation, QueryLog, User


class ConversationRepository:
    """PostgreSQL access for conversations, messages, and query logs."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user: User, conversation_id: str | None) -> Conversation:
        if conversation_id:
            conv = (
                self.db.query(Conversation)
                .filter(
                    Conversation.id == uuid.UUID(conversation_id),
                    Conversation.user_id == user.id,
                )
                .first()
            )
            if conv:
                return conv

        conv = Conversation(user_id=user.id, title="New conversation")
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def add_exchange(
        self,
        conversation: Conversation,
        question: str,
        answer: str,
        sources: list[str],
    ) -> None:
        if conversation.title == "New conversation":
            conversation.title = question[:80]
        conversation.updated_at = datetime.utcnow()
        self.db.add(ChatMessage(conversation_id=conversation.id, role="user", content=question))
        self.db.add(
            ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                sources=sources,
            )
        )
        self.db.commit()

    def list_conversations(self, user: User) -> list[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def get_messages(self, user: User, conversation_id: str) -> list[ChatMessage]:
        conv = (
            self.db.query(Conversation)
            .filter(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == user.id,
            )
            .first()
        )
        if not conv:
            return []
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conv.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    def log_query(
        self,
        user: User,
        question: str,
        document_id: str | None,
        elapsed_ms: float,
        tokens: int,
        cached: bool,
    ) -> None:
        self.db.add(
            QueryLog(
                user_id=user.id,
                question=question,
                document_id=uuid.UUID(document_id) if document_id else None,
                response_time_ms=round(elapsed_ms, 2),
                tokens_used=tokens,
                cached=cached,
            )
        )
        self.db.commit()
