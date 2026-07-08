import logging

from app.core.config import config

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Optional full-text index (disabled unless ELASTICSEARCH_URL is set)."""

    @staticmethod
    def is_enabled() -> bool:
        return config.ELASTICSEARCH_ENABLED

    @staticmethod
    def index_document(document_id: str, filename: str, chunks: list[str]) -> None:
        if not config.ELASTICSEARCH_ENABLED:
            return
        logger.info("Elasticsearch indexing skipped (stub): %s", document_id)

    @staticmethod
    def search(query: str, limit: int = 10) -> list[dict]:
        if not config.ELASTICSEARCH_ENABLED:
            return []
        return []
