"""LLM layer — delegates to LangChain Groq integration."""

from typing import Generator

from langchain_core.messages import HumanMessage

from app.rag.llm import enhance_search_query, get_chat_llm, invoke_llm, stream_llm


class LLMService:
    """Backward-compatible facade over LangChain ChatGroq."""

    @staticmethod
    def complete(prompt: str, temperature: float | None = None) -> tuple[str, int]:
        from app.core.config import config

        if temperature is not None:
            llm = get_chat_llm()
            llm.temperature = temperature
        messages = [HumanMessage(content=prompt)]
        return invoke_llm(messages)

    @staticmethod
    def complete_stream(prompt: str, temperature: float | None = None) -> Generator[str, None, tuple[str, int]]:
        messages = [HumanMessage(content=prompt)]
        return stream_llm(messages)

    @staticmethod
    def enhance_search_query(query: str) -> str:
        return enhance_search_query(query)
