import logging
from typing import Generator

from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import config
from app.rag.prompts import SEARCH_REWRITE_PROMPT

logger = logging.getLogger(__name__)


def _groq_kwargs() -> dict:
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")
    return {
        "model": config.GROQ_MODEL,
        "groq_api_key": config.GROQ_API_KEY,
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "max_retries": config.LLM_MAX_RETRIES,
    }


def get_chat_llm() -> ChatGroq:
    return ChatGroq(**_groq_kwargs())


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def invoke_llm(messages: list[BaseMessage]) -> tuple[str, int]:
    llm = get_chat_llm()
    response = llm.invoke(messages)
    text = response.content if isinstance(response.content, str) else str(response.content)
    tokens = 0
    if response.response_metadata and "token_usage" in response.response_metadata:
        usage = response.response_metadata["token_usage"]
        tokens = usage.get("total_tokens", 0)
    return text, tokens


def stream_llm(messages: list[BaseMessage]) -> Generator[str, None, tuple[str, int]]:
    llm = get_chat_llm()
    parts: list[str] = []
    for chunk in llm.stream(messages):
        delta = chunk.content if isinstance(chunk.content, str) else str(chunk.content or "")
        if delta:
            parts.append(delta)
            yield delta
    return "".join(parts), 0


def enhance_search_query(query: str) -> str:
    try:
        chain = SEARCH_REWRITE_PROMPT | get_chat_llm()
        result = chain.invoke({"query": query})
        refined = (result.content if hasattr(result, "content") else str(result)).strip().strip('"')
        return refined or query
    except Exception as exc:
        logger.warning("Search query enhancement failed: %s", exc)
        return query
