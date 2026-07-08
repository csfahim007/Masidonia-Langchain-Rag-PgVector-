import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import Document, User
from app.repositories.document_repository import DocumentRepository
from app.services.document_parser import (
    chunk_text,
    compute_file_hash,
    extract_text,
    guess_category,
    suggest_tags,
    validate_file,
    _content_type,
)
from app.rag.embeddings import embed_documents
from app.services.elasticsearch_service import ElasticsearchService
from app.services.object_storage_service import ObjectStorageService

logger = logging.getLogger(__name__)


class DocumentService:

    @staticmethod
    def list_documents(db: Session, user: User, folder_id: str | None = None) -> list[Document]:
        return DocumentRepository(db).list_by_user(user, folder_id)

    @staticmethod
    def get_document(db: Session, user: User, document_id: str) -> Document | None:
        return DocumentRepository(db).get_by_id(user, document_id)

    @staticmethod
    def delete_document(db: Session, user: User, document_id: str) -> bool:
        repo = DocumentRepository(db)
        doc = repo.get_by_id(user, document_id)
        if not doc:
            return False
        if doc.file_path:
            try:
                ObjectStorageService.delete(doc.file_path)
            except Exception as e:
                logger.warning("Could not delete file %s: %s", doc.file_path, e)
        repo.delete(doc)
        return True

    @staticmethod
    def process_upload(
        db: Session,
        user: User,
        filename: str,
        content: bytes,
        folder_id: str | None = None,
    ) -> Document:
        validate_file(filename, len(content))
        file_hash = compute_file_hash(content)
        repo = DocumentRepository(db)

        existing = repo.find_by_hash(user, file_hash)
        if existing:
            raise ValueError("This document has already been uploaded")

        doc_id = uuid.uuid4()
        file_path = ObjectStorageService.save(str(user.id), str(doc_id), filename, content)
        text = extract_text(filename, content)
        if not text:
            raise ValueError("Could not extract text from document")

        category = guess_category(text, filename)
        tags = suggest_tags(text, category)
        chunks = chunk_text(text)

        document = Document(
            id=doc_id,
            user_id=user.id,
            folder_id=uuid.UUID(folder_id) if folder_id else None,
            filename=filename,
            title=filename.rsplit(".", 1)[0],
            content_type=_content_type(filename),
            file_path=file_path,
            file_size=len(content),
            file_hash=file_hash,
            status="processing",
            category=category,
            tags=tags,
            metadata_json={"word_count": len(text.split()), "char_count": len(text)},
            uploaded_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        repo.create(document)

        embeddings = embed_documents(chunks)
        chunk_pairs = list(zip(chunks, embeddings))
        repo.add_chunks(document.id, chunk_pairs)
        ElasticsearchService.index_document(str(document.id), filename, chunks)
        repo.mark_ready(document, len(chunks))
        return document

    @staticmethod
    def update_document(
        db: Session,
        user: User,
        document_id: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> Document | None:
        repo = DocumentRepository(db)
        doc = repo.get_by_id(user, document_id)
        if not doc:
            return None
        if title is not None:
            title = title.strip()
            if not title:
                raise ValueError("Title cannot be empty")
            doc.title = title
        if tags is not None:
            doc.tags = tags
        doc.updated_at = datetime.utcnow()
        repo.commit()
        repo.refresh(doc)
        return doc

    @staticmethod
    def process_bulk_upload(
        db: Session,
        user: User,
        files: list[tuple[str, bytes]],
        folder_id: str | None = None,
    ) -> list[dict]:
        results = []
        for filename, content in files:
            try:
                document = DocumentService.process_upload(
                    db, user, filename, content, folder_id
                )
                results.append({
                    "filename": filename,
                    "status": "success",
                    "document_id": str(document.id),
                    "chunks_created": document.chunks_count,
                    "category": document.category,
                })
            except ValueError as e:
                results.append({
                    "filename": filename,
                    "status": "error",
                    "error": str(e),
                })
            except Exception:
                logger.exception("Bulk upload failed for %s", filename)
                results.append({
                    "filename": filename,
                    "status": "error",
                    "error": "Processing failed",
                })
        return results
