import hashlib
import io
import logging
import re
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.core.config import config
from app.rag.ingest import split_text

logger = logging.getLogger(__name__)


def ensure_upload_dir() -> Path:
    path = Path(config.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_file(filename: str, size: int) -> None:
    ext = get_file_extension(filename)
    if ext not in config.ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type. Allowed: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}")
    if size > config.MAX_FILE_SIZE:
        raise ValueError(f"File too large. Max size: {config.MAX_FILE_SIZE // (1024 * 1024)} MB")


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text)
    return clean_text("\n".join(parts))


def extract_text_from_docx(content: bytes) -> str:
    doc = DocxDocument(io.BytesIO(content))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return clean_text("\n".join(parts))


def extract_text_from_plain(content: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return clean_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode text file")


def extract_text(filename: str, content: bytes) -> str:
    ext = get_file_extension(filename)
    if ext == ".pdf":
        return extract_text_from_pdf(content)
    if ext == ".docx":
        return extract_text_from_docx(content)
    if ext in {".txt", ".md", ".markdown"}:
        return extract_text_from_plain(content)
    raise ValueError(f"Unsupported extension: {ext}")


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """Split text using LangChain RecursiveCharacterTextSplitter."""
    if chunk_size or overlap:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or config.CHUNK_SIZE,
            chunk_overlap=overlap or config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text(text) if text.strip() else []
    return split_text(text)


def guess_category(text: str, filename: str) -> str:
    lowered = f"{filename} {text[:2000]}".lower()
    if any(k in lowered for k in ("resume", "cv", "curriculum vitae", "experience", "skills")):
        return "resume"
    if any(k in lowered for k in ("invoice", "receipt", "payment")):
        return "finance"
    if any(k in lowered for k in ("report", "analysis", "summary")):
        return "report"
    return "general"


def suggest_tags(text: str, category: str) -> list[str]:
    tags = {category}
    keywords = {
        "python": "python",
        "javascript": "javascript",
        "react": "react",
        "machine learning": "ml",
        "data": "data",
        "project": "projects",
        "education": "education",
        "certification": "certifications",
    }
    lowered = text.lower()
    for needle, tag in keywords.items():
        if needle in lowered:
            tags.add(tag)
    return sorted(tags)[:8]


def _content_type(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    mapping = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "md": "text/markdown",
        "markdown": "text/markdown",
    }
    return mapping.get(ext, "application/octet-stream")
