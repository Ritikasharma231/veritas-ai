"""Lightweight in-memory rate limiter + optional API-key auth middleware."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.rpm:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down and retry."},
            )
        window.append(now)
        return await call_next(request)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """If API_KEYS is configured, require X-API-Key on mutating endpoints."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        keys = settings.api_key_set
        if not keys:
            return await call_next(request)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        provided = request.headers.get("x-api-key", "")
        if provided not in keys:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)
