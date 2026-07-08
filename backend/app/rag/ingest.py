from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import config


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_text(text: str) -> list[str]:
    if not text.strip():
        return []
    return get_text_splitter().split_text(text)
