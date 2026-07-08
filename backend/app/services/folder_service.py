import uuid

from sqlalchemy.orm import Session

from app.core.database import Document, Folder, User


class FolderService:

    @staticmethod
    def list_folders(db: Session, user: User, parent_id: str | None = None) -> list[Folder]:
        query = db.query(Folder).filter(Folder.user_id == user.id)
        if parent_id:
            query = query.filter(Folder.parent_id == uuid.UUID(parent_id))
        else:
            query = query.filter(Folder.parent_id.is_(None))
        return query.order_by(Folder.name.asc()).all()

    @staticmethod
    def get_folder(db: Session, user: User, folder_id: str) -> Folder | None:
        return (
            db.query(Folder)
            .filter(Folder.id == uuid.UUID(folder_id), Folder.user_id == user.id)
            .first()
        )

    @staticmethod
    def create_folder(
        db: Session,
        user: User,
        name: str,
        parent_id: str | None = None,
    ) -> Folder:
        name = name.strip()
        if not name:
            raise ValueError("Folder name is required")

        parent_uuid = None
        if parent_id:
            parent = FolderService.get_folder(db, user, parent_id)
            if not parent:
                raise ValueError("Parent folder not found")
            parent_uuid = parent.id

        folder = Folder(user_id=user.id, name=name, parent_id=parent_uuid)
        db.add(folder)
        db.commit()
        db.refresh(folder)
        return folder

    @staticmethod
    def rename_folder(db: Session, user: User, folder_id: str, name: str) -> Folder | None:
        folder = FolderService.get_folder(db, user, folder_id)
        if not folder:
            return None
        name = name.strip()
        if not name:
            raise ValueError("Folder name is required")
        folder.name = name
        db.commit()
        db.refresh(folder)
        return folder

    @staticmethod
    def delete_folder(db: Session, user: User, folder_id: str) -> bool:
        folder = FolderService.get_folder(db, user, folder_id)
        if not folder:
            return False

        child_count = (
            db.query(Folder)
            .filter(Folder.parent_id == folder.id, Folder.user_id == user.id)
            .count()
        )
        if child_count:
            raise ValueError("Folder contains subfolders. Remove them first.")

        doc_count = (
            db.query(Document)
            .filter(Document.folder_id == folder.id, Document.user_id == user.id)
            .count()
        )
        if doc_count:
            raise ValueError("Folder contains documents. Move or delete them first.")

        db.delete(folder)
        db.commit()
        return True

    @staticmethod
    def move_document(
        db: Session, user: User, document_id: str, folder_id: str | None
    ) -> Document | None:
        doc = (
            db.query(Document)
            .filter(Document.id == uuid.UUID(document_id), Document.user_id == user.id)
            .first()
        )
        if not doc:
            return None

        if folder_id:
            folder = FolderService.get_folder(db, user, folder_id)
            if not folder:
                raise ValueError("Folder not found")
            doc.folder_id = folder.id
        else:
            doc.folder_id = None

        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def folder_document_counts(db: Session, user: User) -> dict[str, int]:
        rows = (
            db.query(Document.folder_id, Document.id)
            .filter(Document.user_id == user.id, Document.folder_id.isnot(None))
            .all()
        )
        counts: dict[str, int] = {}
        for folder_id, _ in rows:
            key = str(folder_id)
            counts[key] = counts.get(key, 0) + 1
        return counts
