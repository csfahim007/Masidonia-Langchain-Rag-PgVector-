"""Production RAG stack — LangChain orchestration over pgvector + Groq."""

__all__ = ["RAGOrchestrator"]


def __getattr__(name: str):
    if name == "RAGOrchestrator":
        from app.rag.orchestrator import RAGOrchestrator

        return RAGOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
