import logging
from typing import Generator

from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from app.core.database import User
from app.rag.llm import get_chat_llm, stream_llm
from app.rag.prompts import CONTEXTUALIZE_PROMPT, FOLLOWUP_PROMPT, RAG_PROMPT
from app.rag.retriever import (
    PgVectorHybridRetriever,
    format_source_citations,
    hits_from_documents,
)
from app.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """LangChain RAG pipeline: history-aware retrieval → stuff documents → Groq generation."""

    def __init__(
        self,
        db: Session,
        user: User,
        document_id: str | None = None,
    ):
        self.db = db
        self.user = user
        self.document_id = document_id
        self.llm = get_chat_llm()
        self.retriever = PgVectorHybridRetriever(
            db=db,
            user=user,
            document_id=document_id,
        )
        self._conv_repo = ConversationRepository(db)

    def _build_chain(self):
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            self.retriever,
            CONTEXTUALIZE_PROMPT,
        )
        question_answer_chain = create_stuff_documents_chain(self.llm, RAG_PROMPT)
        return create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def _load_chat_history(self, conversation_id: str | None) -> list:
        if not conversation_id:
            return []
        messages = self._conv_repo.get_messages(self.user, conversation_id)
        history = []
        for msg in messages[-10:]:
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history.append(AIMessage(content=msg.content))
        return history

    def invoke(
        self,
        question: str,
        conversation_id: str | None = None,
    ) -> dict:
        chain = self._build_chain()
        chat_history = self._load_chat_history(conversation_id)

        result = chain.invoke({"input": question, "chat_history": chat_history})
        answer = result.get("answer", "")
        context_docs = result.get("context", [])
        sources = format_source_citations(context_docs)
        follow_ups = self._suggest_followups(question, answer, context_docs)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": hits_from_documents(context_docs),
            "follow_up_questions": follow_ups,
            "tokens": 0,
        }

    def stream(
        self,
        question: str,
        conversation_id: str | None = None,
    ) -> Generator[dict, None, dict]:
        """Yield stream events: sources → tokens → final metadata."""
        chain = self._build_chain()
        chat_history = self._load_chat_history(conversation_id)

        final_answer = ""
        context_docs = []

        for chunk in chain.stream({"input": question, "chat_history": chat_history}):
            if "context" in chunk and chunk["context"]:
                context_docs = chunk["context"]
                sources = format_source_citations(context_docs)
                yield {"type": "sources", "sources": sources}

            if "answer" in chunk and chunk["answer"]:
                delta = chunk["answer"]
                final_answer += delta
                yield {"type": "token", "content": delta}

        if not final_answer:
            final_answer = "I could not generate an answer."

        follow_ups = self._suggest_followups(question, final_answer, context_docs)
        sources = format_source_citations(context_docs)

        return {
            "answer": final_answer,
            "sources": sources,
            "chunks": hits_from_documents(context_docs),
            "follow_up_questions": follow_ups,
            "tokens": 0,
        }

    def retrieve(self, query: str, limit: int | None = None) -> list[dict]:
        """Direct hybrid retrieval (for search service compatibility)."""
        if limit:
            self.retriever.k = limit
        docs = self.retriever.invoke(query)
        return hits_from_documents(docs)

    def _suggest_followups(self, question: str, answer: str, context_docs) -> list[str]:
        if not context_docs:
            return ["Upload a document to get started", "What types of files are supported?"]
        try:
            chain = FOLLOWUP_PROMPT | self.llm
            result = chain.invoke({
                "question": question,
                "answer": answer[:500],
            })
            text = result.content if hasattr(result, "content") else str(result)
            lines = [ln.strip().lstrip("0123456789.-) ") for ln in text.splitlines() if ln.strip()]
            return lines[:3] if lines else self._default_followups()
        except Exception as exc:
            logger.warning("Follow-up generation failed: %s", exc)
            return self._default_followups()

    @staticmethod
    def _default_followups() -> list[str]:
        return [
            "Can you summarize the key points?",
            "What skills or qualifications are mentioned?",
            "Are there any gaps or missing information?",
        ]
