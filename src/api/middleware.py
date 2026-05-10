"""
API Middleware

Request logging, rate limiting, and security headers.
"""

import os
import time
import ipaddress
import logging
from collections import defaultdict
from typing import List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ============================================================================
# CLIENT IP RESOLUTION (X-Forwarded-For aware)
# ============================================================================

def _parse_trusted_proxies() -> List:
    """Parse TRUSTED_PROXIES env var into a list of ip_network objects."""
    raw = os.environ.get("TRUSTED_PROXIES", "").strip()
    if not raw:
        return []
    nets = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            # Allow plain IP or CIDR
            if "/" not in entry:
                entry = f"{entry}/32" if ":" not in entry else f"{entry}/128"
            nets.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning(f"Ignoring invalid TRUSTED_PROXIES entry: {entry}")
    return nets


_TRUSTED_PROXIES = _parse_trusted_proxies()


def _is_trusted_proxy(ip_str: Optional[str]) -> bool:
    if not ip_str or not _TRUSTED_PROXIES:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in _TRUSTED_PROXIES)


def get_client_ip(request: Request) -> Optional[str]:
    """Resolve the real client IP, respecting X-Forwarded-For only when the
    direct peer is a trusted proxy (TRUSTED_PROXIES env var, comma-separated
    CIDRs). Otherwise falls back to request.client.host.
    """
    direct_peer = request.client.host if request.client else None
    if _is_trusted_proxy(direct_peer):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Leftmost entry is the original client.
            leftmost = xff.split(",")[0].strip()
            if leftmost:
                return leftmost
    return direct_peer


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

    # Safe defaults: no inline scripts, no eval, allow self + Groq endpoints
    # for fetch (front-end occasionally calls Groq directly during voice flows).
    _CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "media-src 'self' blob:; "
        "connect-src 'self' https://api.groq.com https://api.sarvam.ai; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "microphone=(self), camera=(), geolocation=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = self._CSP
        # Note: X-XSS-Protection deliberately removed (deprecated, can be
        # harmful on legacy browsers). Modern browsers rely on CSP instead.
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
        client_ip = get_client_ip(request) or "unknown"
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
