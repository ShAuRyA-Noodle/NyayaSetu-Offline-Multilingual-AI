"""
API Middleware

Request logging, rate limiting, and security headers.
"""

import time
import logging
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing metrics."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        request.app.state.request_count += 1
        path = request.url.path
        if path not in request.app.state.requests_by_endpoint:
            request.app.state.requests_by_endpoint[path] = 0
        request.app.state.requests_by_endpoint[path] += 1

        logger.info(f"→ {request.method} {path}")

        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"← {request.method} {path} - "
            f"Status: {response.status_code} - Duration: {duration_ms:.2f}ms"
        )
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting per IP."""

    def __init__(self, app, default_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.requests: dict = defaultdict(list)
        self.endpoint_limits = {
            "/api/v1/auth/login": 5,
            "/api/v1/auth/register": 5,
            "/api/v1/auth/forgot-password": 3,
        }

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        now = time.time()

        key = f"{client_ip}:{path}"
        limit = self.endpoint_limits.get(path, self.default_limit)

        # Clean old entries
        self.requests[key] = [
            t for t in self.requests[key]
            if now - t < self.window_seconds
        ]

        # Remove empty keys to prevent memory leak
        if not self.requests[key]:
            del self.requests[key]

        # Cap dict size to prevent unbounded growth
        if len(self.requests) > 10000:
            oldest_keys = sorted(
                self.requests.keys(),
                key=lambda k: self.requests[k][0] if self.requests[k] else 0
            )
            for k in oldest_keys[:5000]:
                del self.requests[k]

        current = self.requests.get(key, [])
        if len(current) >= limit:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": f"Too many requests. Limit: {limit}/{self.window_seconds}s",
                    "detail": "Please try again later"
                }
            )

        self.requests[key].append(now)
        response = await call_next(request)
        return response
