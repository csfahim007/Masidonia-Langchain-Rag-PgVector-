import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import config
from app.core.redis_client import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not redis_client or not request.url.path.startswith("/api/"):
            return await call_next(request)

        if request.url.path in {"/api/health", "/health", "/"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}:{int(time.time()) // config.RATE_LIMIT_WINDOW}"

        try:
            current = redis_client.incr(key)
            if current == 1:
                redis_client.expire(key, config.RATE_LIMIT_WINDOW)
            if current > config.RATE_LIMIT_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."},
                )
        except Exception:
            pass

        return await call_next(request)
