import logging
import ssl
from typing import Any, Optional

import redis

from app.core.config import config

logger = logging.getLogger(__name__)

redis_client: Optional[redis.Redis] = None


def _connection_kwargs(use_ssl: bool) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "decode_responses": True,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    }
    if use_ssl:
        kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
    return kwargs


def _client_from_url(url: str) -> redis.Redis:
    use_ssl = url.startswith("rediss://")
    return redis.from_url(url, **_connection_kwargs(use_ssl))


def _create_redis_client() -> Optional[redis.Redis]:
    if not config.REDIS_URL and not config.REDIS_HOST:
        return None

    if config.REDIS_URL:
        try:
            client = _client_from_url(config.REDIS_URL)
            client.ping()
            return client
        except redis.ConnectionError as exc:
            if (
                config.REDIS_URL.startswith("rediss://")
                and "WRONG_VERSION_NUMBER" in str(exc)
            ):
                plain_url = "redis://" + config.REDIS_URL[len("rediss://") :]
                logger.info(
                    "Redis TLS handshake failed; retrying without SSL for this endpoint"
                )
                client = _client_from_url(plain_url)
                client.ping()
                return client
            raise

    if not config.REDIS_HOST:
        return None

    host_kwargs: dict[str, Any] = {
        "host": config.REDIS_HOST,
        "port": config.REDIS_PORT,
        "username": config.REDIS_USERNAME,
        "password": config.REDIS_PASSWORD,
        "decode_responses": True,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
        "ssl": config.REDIS_USE_SSL,
    }
    if config.REDIS_USE_SSL:
        host_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE

    client = redis.Redis(**host_kwargs)
    client.ping()
    return client


def connect_redis() -> Optional[redis.Redis]:
    """Initialize Redis connection (called on app startup)."""
    global redis_client
    try:
        client = _create_redis_client()
        if client:
            client.ping()
            redis_client = client
            logger.info("✅ Redis Cloud connected successfully")
        else:
            redis_client = None
            logger.info("ℹ️ Redis not configured; caching and token revocation disabled")
    except Exception as exc:
        logger.warning("⚠️ Redis Cloud connection failed: %s", exc)
        redis_client = None
    return redis_client


def disconnect_redis() -> None:
    """Close Redis connection (called on app shutdown)."""
    global redis_client
    if redis_client:
        try:
            redis_client.close()
            logger.info("Redis connection closed")
        except Exception as exc:
            logger.warning("Error closing Redis connection: %s", exc)
        finally:
            redis_client = None


# Eager connect for scripts and tests; main app also reconnects via lifespan
connect_redis()


def get_redis() -> Optional[redis.Redis]:
    return redis_client


def is_redis_available() -> bool:
    if redis_client is None:
        return False
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


class RedisKeys:
    AUTH_REFRESH = "auth:refresh:{user_id}"
    AUTH_BLACKLIST = "auth:blacklist:{token}"
