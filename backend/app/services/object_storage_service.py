import logging
import re
from pathlib import Path

from app.core.config import config

logger = logging.getLogger(__name__)


class ObjectStorageService:
    """Raw document storage: local filesystem or S3/MinIO."""

    @staticmethod
    def _safe_name(filename: str) -> str:
        return re.sub(r"[^\w.\-]", "_", filename)

    @staticmethod
    def _object_key(user_id: str, document_id: str, filename: str) -> str:
        return f"{user_id}/{document_id}_{ObjectStorageService._safe_name(filename)}"

    @staticmethod
    def save(user_id: str, document_id: str, filename: str, content: bytes) -> str:
        if config.STORAGE_BACKEND == "s3":
            return ObjectStorageService._save_s3(user_id, document_id, filename, content)
        return ObjectStorageService._save_local(user_id, document_id, filename, content)

    @staticmethod
    def delete(storage_path: str) -> None:
        if config.STORAGE_BACKEND == "s3" or storage_path.startswith("s3://"):
            ObjectStorageService._delete_s3(storage_path)
        else:
            ObjectStorageService._delete_local(storage_path)

    @staticmethod
    def _save_local(user_id: str, document_id: str, filename: str, content: bytes) -> str:
        upload_dir = Path(config.UPLOAD_DIR) / user_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{document_id}_{ObjectStorageService._safe_name(filename)}"
        file_path.write_bytes(content)
        return str(file_path)

    @staticmethod
    def _delete_local(storage_path: str) -> None:
        try:
            path = Path(storage_path)
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning("Could not delete local file %s: %s", storage_path, exc)

    @staticmethod
    def _s3_client():
        import boto3
        from botocore.client import Config

        if not config.S3_ENDPOINT or not config.S3_ACCESS_KEY or not config.S3_SECRET_KEY:
            raise ValueError("S3/MinIO credentials are not configured")

        return boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            region_name=config.S3_REGION,
            config=Config(signature_version="s3v4"),
            use_ssl=config.S3_USE_SSL,
        )

    @staticmethod
    def _save_s3(user_id: str, document_id: str, filename: str, content: bytes) -> str:
        client = ObjectStorageService._s3_client()
        key = ObjectStorageService._object_key(user_id, document_id, filename)
        client.put_object(Bucket=config.S3_BUCKET, Key=key, Body=content)
        return f"s3://{config.S3_BUCKET}/{key}"

    @staticmethod
    def _delete_s3(storage_path: str) -> None:
        try:
            if not storage_path.startswith("s3://"):
                return
            _, _, rest = storage_path.partition("s3://")
            bucket, _, key = rest.partition("/")
            client = ObjectStorageService._s3_client()
            client.delete_object(Bucket=bucket, Key=key)
        except Exception as exc:
            logger.warning("Could not delete S3 object %s: %s", storage_path, exc)
