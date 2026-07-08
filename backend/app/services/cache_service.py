import json
import logging
from typing import Any, Optional

from app.core.config import config
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache layer for sessions, rate limits, and response caching."""

    PREFIX = "cache:"

    @staticmethod
    def _key(key: str) -> str:
        return f"{CacheService.PREFIX}{key}"

    @staticmethod
    def get(key: str) -> Optional[str]:
        if not redis_client:
            return None
        try:
            return redis_client.get(CacheService._key(key))
        except Exception as exc:
            logger.error("Cache get failed for %s: %s", key, exc)
            return None

    @staticmethod
    def set(key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        if not redis_client:
            return False
        try:
            ttl = ttl_seconds if ttl_seconds is not None else config.REDIS_CACHE_TTL_SECONDS
            redis_client.setex(CacheService._key(key), ttl, value)
            return True
        except Exception as exc:
            logger.error("Cache set failed for %s: %s", key, exc)
            return False

    @staticmethod
    def delete(key: str) -> bool:
        if not redis_client:
            return False
        try:
            redis_client.delete(CacheService._key(key))
            return True
        except Exception as exc:
            logger.error("Cache delete failed for %s: %s", key, exc)
            return False

    @staticmethod
    def get_json(key: str) -> Optional[Any]:
        raw = CacheService.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in cache key %s", key)
            return None

    @staticmethod
    def set_json(key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        try:
            return CacheService.set(key, json.dumps(value), ttl_seconds=ttl_seconds)
        except (TypeError, ValueError) as exc:
            logger.error("Cache set_json failed for %s: %s", key, exc)
            return False

    @staticmethod
    def get_embedding(key: str) -> Optional[list[float]]:
        data = CacheService.get_json(f"embedding:{key}")
        return data if isinstance(data, list) else None

    @staticmethod
    def set_embedding(key: str, vector: list[float], ttl_seconds: int = 86400) -> bool:
        return CacheService.set_json(f"embedding:{key}", vector, ttl_seconds=ttl_seconds)
