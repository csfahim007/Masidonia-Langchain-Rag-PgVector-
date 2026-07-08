import json
import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.core.database import Conversation, User
from app.rag.orchestrator import RAGOrchestrator
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.vector_repository import VectorRepository
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

# Bump when retrieval logic changes to avoid serving stale empty-context cached answers
_CHAT_CACHE_VERSION = "v2"


class RAGService:
    """Production RAG service — LangChain orchestration with pgvector + Groq."""

    @staticmethod
    def _orchestrator(db: Session, user: User, document_id: str | None = None) -> RAGOrchestrator:
        return RAGOrchestrator(db, user, document_id)

    @staticmethod
    def retrieve_chunks(db: Session, user: User, query: str, document_id: str | None = None, limit: int = 5) -> list[dict]:
        return VectorRepository(db).similarity_search(user, query, document_id, limit)

    @staticmethod
    def keyword_search_chunks(db: Session, user: User, query: str, document_id: str | None = None, limit: int = 5) -> list[dict]:
        return VectorRepository(db).keyword_search(user, query, document_id, limit)

    @staticmethod
    def hybrid_retrieve(db: Session, user: User, query: str, document_id: str | None = None, limit: int = 5) -> list[dict]:
        return RAGService._orchestrator(db, user, document_id).retrieve(query, limit)

    @staticmethod
    def chat(
        db: Session,
        user: User,
        question: str,
        document_id: str | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        start = time.time()
        cache_key = f"chat:{_CHAT_CACHE_VERSION}:{user.id}:{document_id or 'all'}:{question.strip().lower()}"
        conv_repo = ConversationRepository(db)

        cached = CacheService.get_json(cache_key)
        if cached:
            conv_repo.log_query(user, question, document_id, (time.time() - start) * 1000, 0, True)
            return cached

        orchestrator = RAGService._orchestrator(db, user, document_id)
        rag_result = orchestrator.invoke(question, conversation_id)

        conversation = conv_repo.get_or_create(user, conversation_id)
        conv_repo.add_exchange(conversation, question, rag_result["answer"], rag_result["sources"])

        result = {
            "answer": rag_result["answer"],
            "sources": rag_result["sources"],
            "conversation_id": str(conversation.id),
            "follow_up_questions": rag_result["follow_up_questions"],
        }
        CacheService.set_json(cache_key, result)
        conv_repo.log_query(
            user, question, document_id,
            (time.time() - start) * 1000,
            rag_result.get("tokens", 0),
            False,
        )
        return result

    @staticmethod
    def chat_stream(db: Session, user: User, question: str, document_id: str | None = None, conversation_id: str | None = None):
        start = time.time()
        cache_key = f"chat:{_CHAT_CACHE_VERSION}:{user.id}:{document_id or 'all'}:{question.strip().lower()}"
        conv_repo = ConversationRepository(db)

        cached = CacheService.get_json(cache_key)
        if cached:
            conv_repo.log_query(user, question, document_id, (time.time() - start) * 1000, 0, True)
            yield json.dumps({"type": "sources", "sources": cached.get("sources", [])})
            yield json.dumps({"type": "token", "content": cached.get("answer", "")})
            yield json.dumps({
                "type": "done",
                "conversation_id": cached.get("conversation_id", ""),
                "follow_up_questions": cached.get("follow_up_questions", []),
            })
            return

        orchestrator = RAGService._orchestrator(db, user, document_id)
        stream = orchestrator.stream(question, conversation_id)
        final: dict = {}

        try:
            while True:
                event = next(stream)
                yield json.dumps(event)
        except StopIteration as exc:
            final = exc.value if exc.value else {}

        answer = final.get("answer", "")
        sources = final.get("sources", [])
        follow_ups = final.get("follow_up_questions", [])

        conversation = conv_repo.get_or_create(user, conversation_id)
        conv_repo.add_exchange(conversation, question, answer, sources)

        result = {
            "answer": answer,
            "sources": sources,
            "conversation_id": str(conversation.id),
            "follow_up_questions": follow_ups,
        }
        CacheService.set_json(cache_key, result)
        conv_repo.log_query(user, question, document_id, (time.time() - start) * 1000, final.get("tokens", 0), False)

        yield json.dumps({
            "type": "done",
            "conversation_id": str(conversation.id),
            "follow_up_questions": follow_ups,
        })

    @staticmethod
    def list_conversations(db: Session, user: User):
        return ConversationRepository(db).list_conversations(user)

    @staticmethod
    def get_conversation_messages(db: Session, user: User, conversation_id: str):
        return ConversationRepository(db).get_messages(user, conversation_id)

    @staticmethod
    def delete_conversation(db: Session, user: User, conversation_id: str) -> bool:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == user.id,
            )
            .first()
        )
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        return True
