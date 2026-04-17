"""
Post-deploy smoke test.

Hits every critical endpoint on the live backend + checks the frontend is reachable.
Prints a clean pass/fail report.

Usage:
    API_URL="https://nyayasetu-api.onrender.com" \
    FRONTEND_URL="https://nyayasetu.vercel.app" \
    python scripts/smoke_test.py

Exit code 0 if every check passes, 1 otherwise.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from typing import Any, Callable

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(2)

API_URL = os.environ.get("API_URL", "http://localhost:8001").rstrip("/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

_passed = 0
_failed = 0


def _check(label: str, condition: bool, detail: str = ""):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  {GREEN}PASS{RESET}  {label}")
    else:
        _failed += 1
        print(f"  {RED}FAIL{RESET}  {label}" + (f"  -> {detail}" if detail else ""))


def _try(label: str, fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except Exception as e:
        _check(label, False, f"exception: {e}")
        return None


def section(title: str):
    print(f"\n{BOLD}--- {title} ---{RESET}")


def check_health():
    section("Backend reachability")
    t0 = time.time()
    r = _try("GET /health", lambda: requests.get(f"{API_URL}/health", timeout=60))
    if r is None:
        return
    elapsed = time.time() - t0
    _check(f"health endpoint 200 (took {elapsed:.1f}s)", r.status_code == 200, f"got {r.status_code}")
    if elapsed > 10:
        print(f"  {YELLOW}NOTE{RESET}  Slow first request - likely Render cold start. Subsequent requests should be fast.")


def check_docs():
    section("API docs served")
    r = _try("GET /docs", lambda: requests.get(f"{API_URL}/docs", timeout=30))
    if r:
        _check("Swagger UI reachable", r.status_code == 200)


def check_cors():
    section("CORS configured")
    if not FRONTEND_URL:
        print(f"  {YELLOW}SKIP{RESET}  FRONTEND_URL not set")
        return
    r = _try(
        "OPTIONS /health with Origin",
        lambda: requests.options(
            f"{API_URL}/health",
            headers={
                "Origin": FRONTEND_URL,
                "Access-Control-Request-Method": "GET",
            },
            timeout=30,
        ),
    )
    if r is None:
        return
    allowed = r.headers.get("Access-Control-Allow-Origin", "")
    ok = allowed == FRONTEND_URL or allowed == "*"
    _check(
        f"Access-Control-Allow-Origin includes {FRONTEND_URL}",
        ok,
        f"header was: {allowed!r}",
    )


def check_auth_flow():
    section("Auth flow (register + login)")
    # Use a random throwaway user so repeat runs don't collide
    uid = uuid.uuid4().hex[:8]
    username = f"smoketest_{uid}"
    email = f"smoke_{uid}@test.local"
    password = "SmokeTest1234!"

    r = _try(
        "POST /api/v1/auth/register",
        lambda: requests.post(
            f"{API_URL}/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "role": "citizen",
            },
            timeout=30,
        ),
    )
    if r is None:
        return None
    _check("registration succeeds (201 or 200)", r.status_code in (200, 201), f"body: {r.text[:200]}")

    r = _try(
        "POST /api/v1/auth/login",
        lambda: requests.post(
            f"{API_URL}/api/v1/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        ),
    )
    if r is None or r.status_code != 200:
        _check("login succeeds", False, f"status: {r.status_code if r else 'no response'}")
        return None
    _check("login returns 200", True)
    token = r.json().get("access_token") or r.json().get("token")
    _check("login returns access_token", bool(token))
    return token


def check_authenticated_endpoints(token: str | None):
    if not token:
        print(f"\n{YELLOW}Skipping authenticated endpoint checks (no token){RESET}")
        return
    section("Authenticated endpoints")
    headers = {"Authorization": f"Bearer {token}"}

    r = _try(
        "GET /api/v1/auth/me",
        lambda: requests.get(f"{API_URL}/api/v1/auth/me", headers=headers, timeout=30),
    )
    if r:
        _check("/auth/me returns 200", r.status_code == 200)

    r = _try(
        "GET /api/v1/schemes/list",
        lambda: requests.get(f"{API_URL}/api/v1/schemes/list", headers=headers, timeout=30),
    )
    if r:
        _check("/schemes/list reachable", r.status_code in (200, 404))


def check_groq_reachable():
    section("LLM (Groq) integration")
    # Use a cheap query endpoint if exposed. Fallback: just make sure /health reports llm state.
    r = _try("GET /health", lambda: requests.get(f"{API_URL}/health", timeout=30))
    if r and r.status_code == 200:
        try:
            body = r.json()
            llm_status = body.get("llm") or body.get("services", {}).get("llm")
            if llm_status is not None:
                _check("health reports LLM status", True)
                print(f"  LLM status: {llm_status}")
            else:
                print(f"  {YELLOW}INFO{RESET}  health endpoint doesn't expose LLM status (not a failure)")
        except Exception:
            pass


def check_frontend():
    if not FRONTEND_URL:
        return
    section("Frontend reachability")
    r = _try("GET FRONTEND_URL/", lambda: requests.get(f"{FRONTEND_URL}/", timeout=30))
    if r:
        _check("frontend returns 200", r.status_code == 200)
        _check("frontend serves HTML", "<!doctype html" in r.text.lower() or "<html" in r.text.lower())


def main():
    print(f"\n{BOLD}NyayaSetu Smoke Test{RESET}")
    print(f"API:      {API_URL}")
    print(f"Frontend: {FRONTEND_URL or '(not set)'}")

    check_health()
    check_docs()
    check_cors()
    token = check_auth_flow()
    check_authenticated_endpoints(token)
    check_groq_reachable()
    check_frontend()

    print(f"\n{BOLD}Summary:{RESET} {GREEN}{_passed} passed{RESET}, {RED}{_failed} failed{RESET}\n")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
