"""
Basic rate limiting middleware.

A fixed-window limiter keyed by client IP, held in process memory.
This is intentionally simple: it protects a single-process deployment
against basic abuse (e.g. credential-stuffing against /auth/login)
but does NOT coordinate across multiple worker processes/instances --
a production deployment running more than one process needs a shared
store (Redis, etc.) for this to be effective platform-wide. Documented
as a known limitation in the Phase 11 report rather than presented as
a complete solution.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window_seconds

        hits = self._hits[client_ip]
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again shortly."},
            )

        hits.append(now)
        return await call_next(request)
