"""
Sweep every major API endpoint the frontend hits, testing that each returns
successfully against the current backend. Designed to catch Postgres-vs-SQLite
compatibility issues that only surface at runtime.

Usage:
    API_URL=http://127.0.0.1:8001 python scripts/sweep_endpoints.py
"""
from __future__ import annotations

import os
import sys
import json
import uuid
import requests

API = os.environ.get("API_URL", "http://127.0.0.1:8001").rstrip("/")

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

_passed = 0
_failed = 0
_failures: list[tuple[str, str]] = []


def hit(label: str, method: str, path: str, token: str | None = None,
        json_body: dict | None = None, params: dict | None = None,
        expect_ok: bool = True, timeout: int = 60):
    global _passed, _failed
    url = f"{API}{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.request(method, url, headers=headers, json=json_body, params=params, timeout=timeout)
    except Exception as e:
        _failed += 1
        _failures.append((label, f"{method} {path} -> exception: {e}"))
        print(f"  {RED}FAIL{RESET}  {label}  exception: {e}")
        return None
    ok = (200 <= r.status_code < 300) if expect_ok else (r.status_code >= 400)
    if ok:
        _passed += 1
        print(f"  {GREEN}PASS{RESET}  {label}  {DIM}({r.status_code}){RESET}")
    else:
        _failed += 1
        body_preview = r.text[:200].replace("\n", " ")
        _failures.append((label, f"{method} {path} -> {r.status_code}: {body_preview}"))
        print(f"  {RED}FAIL{RESET}  {label}  {DIM}({r.status_code}){RESET}  {body_preview}")
    return r


def section(title: str):
    print(f"\n{BOLD}--- {title} ---{RESET}")


def main():
    print(f"{BOLD}Nyaya Endpoint Sweep{RESET}")
    print(f"API: {API}\n")

    section("Public endpoints")
    hit("GET /health",           "GET", "/health")
    hit("GET /",                 "GET", "/")
    hit("GET /docs",             "GET", "/docs")
    hit("GET /api/v1/schemes/list", "GET", "/api/v1/schemes/list")
    hit("GET /api/v1/notices/public", "GET", "/api/v1/notices/public")

    section("Auth flow")
    uid = uuid.uuid4().hex[:6]
    citizen = f"sweep_c_{uid}"
    citizen_email = f"sweep_c_{uid}@example.com"
    hit("Register citizen", "POST", "/api/v1/auth/register",
        json_body={"username": citizen, "email": citizen_email, "password": "Sweep123!", "role": "citizen"})

    login = requests.post(f"{API}/api/v1/auth/login",
                         json={"username": citizen, "password": "Sweep123!"}, timeout=30)
    citizen_token = None
    if login.status_code == 200:
        data = login.json()
        citizen_token = data.get("access_token") or data.get("token")
        print(f"  {GREEN}PASS{RESET}  Login citizen  {DIM}(token length: {len(citizen_token or '')}){RESET}")
        globals()["_passed"] = _passed + 1
    else:
        print(f"  {RED}FAIL{RESET}  Login citizen  {login.status_code}")
        return 1

    section("Authenticated - citizen")
    hit("GET /auth/me",                  "GET",  "/api/v1/auth/me", citizen_token)
    hit("GET /grievances/my",            "GET",  "/api/v1/grievances/my", citizen_token)
    hit("GET /nyayavaani/schemes",       "GET",  "/api/v1/nyayavaani/schemes", citizen_token)

    section("Submit grievance (heavy write path)")
    gr = hit("POST /grievances/submit",  "POST", "/api/v1/grievances/submit", citizen_token,
             json_body={"description": "Test grievance from sweep script. Water supply issue.",
                        "title": "Sweep test", "language": "en"})
    grievance_id = None
    if gr and gr.status_code == 200:
        grievance_id = gr.json().get("grievance_id")

    section("Grievance detail + SLA")
    if grievance_id:
        hit(f"GET /grievances/{grievance_id}",    "GET", f"/api/v1/grievances/{grievance_id}", citizen_token)

    section("Schemes detail")
    hit("GET schemes summary",                         "POST", "/api/v1/summarize", citizen_token,
        json_body={"scheme_name": "PM-KISAN", "language": "en"})
    hit("GET scheme full document",                    "GET",
        "/api/v1/schemes/by-name/PM-KISAN/document", citizen_token)
    hit("GET scheme full document (formatted)",        "GET",
        "/api/v1/schemes/by-name/PM-KISAN/document", citizen_token,
        params={"formatted": "true"}, timeout=120)

    section("Notices")
    hit("GET /notices",                                "GET", "/api/v1/notices", citizen_token)

    section("Admin-only endpoints (expect 403 for citizen)")
    hit("GET /admin/stats (should 403)",               "GET", "/api/v1/admin/stats", citizen_token, expect_ok=False)
    hit("GET /admin/analytics/trends (should 403)",    "GET", "/api/v1/admin/analytics/trends",
        citizen_token, expect_ok=False)

    # Try with the pre-migrated admin (unknown password - just check 401, proving query works)
    section("Admin login endpoint reachable")
    r = requests.post(f"{API}/api/v1/auth/login",
                     json={"username": "admin", "password": "definitely_wrong"}, timeout=30)
    if r.status_code == 401:
        print(f"  {GREEN}PASS{RESET}  admin login query runs (401 as expected)")
        globals()["_passed"] = _passed + 1
    else:
        print(f"  {YELLOW}WARN{RESET}  admin login got {r.status_code}: {r.text[:150]}")

    print(f"\n{BOLD}Summary:{RESET} {GREEN}{_passed} passed{RESET}, {RED}{_failed} failed{RESET}\n")
    if _failures:
        print(f"{BOLD}Failures:{RESET}")
        for label, detail in _failures:
            print(f"  {RED}-{RESET} {label}:  {detail}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
