"""
myScheme API client — real scheme data from the National myScheme portal.

The public site at https://www.myscheme.gov.in is a Next.js frontend that talks
to a backend API at https://api.myscheme.gov.in. The API requires an
``x-api-key`` header plus a matching Origin/Referer. The key is embedded in the
frontend JS bundle and rotates on deploys, so this client extracts it live from
the site on each run (with a cached fallback), making the scraper resilient to
key rotation.

Endpoints used:
- Search (list):   GET  /search/v5/schemes?lang=en&q=[]&keyword=&sort=&from=F&size=S
- Detail (single): GET  /schemes/v5/public/schemes?slug=SLUG&lang=en

Stdlib-only (urllib) so it runs in any environment without extra dependencies.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Dict, Iterator, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# The site host (frontend) and API host.
SITE_BASE = "https://www.myscheme.gov.in"
API_BASE = "https://api.myscheme.gov.in"

# Last-known-good key. Only used if live extraction fails. The client always
# tries to extract a fresh key from the site first.
FALLBACK_API_KEY = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"


class MySchemeError(RuntimeError):
    """Raised when the myScheme API cannot be reached or returns an error."""


class MySchemeClient:
    """
    Client for the myScheme public API.

    Handles live API-key extraction, gzip, retries with backoff (the API host
    intermittently resets connections), and polite rate limiting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        request_delay: float = 0.4,
        max_retries: int = 5,
        timeout: int = 30,
    ):
        """
        Args:
            api_key: Explicit key. If None, extracted live from the site.
            request_delay: Seconds to sleep between requests (politeness).
            max_retries: Retry attempts per request on transient failures.
            timeout: Per-request timeout in seconds.
        """
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        # Some corporate/edu networks MITM TLS; be permissive on verification
        # but keep HTTPS. The data is public and read-only.
        self._ssl = ssl.create_default_context()
        self._ssl.check_hostname = False
        self._ssl.verify_mode = ssl.CERT_NONE
        self._api_key = api_key or self._extract_api_key()

    # ----------------------------------------------------------------- HTTP

    def _headers(self, api: bool) -> Dict[str, str]:
        base = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip",
        }
        if api:
            base.update(
                {
                    "x-api-key": self._api_key,
                    "Origin": SITE_BASE,
                    "Referer": SITE_BASE + "/",
                }
            )
        return base

    def _raw_get(self, url: str, api: bool) -> bytes:
        req = urllib.request.Request(url, headers=self._headers(api))
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            return data

    def _get(self, url: str, api: bool = True) -> bytes:
        """GET with retry/backoff on transient failures (resets, 5xx, 429)."""
        last: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                out = self._raw_get(url, api)
                if self.request_delay:
                    time.sleep(self.request_delay)
                return out
            except urllib.error.HTTPError as e:
                last = e
                # 4xx other than 429 are not worth retrying (except transient 403
                # the API sometimes throws under load).
                if e.code not in (403, 429, 500, 502, 503, 504):
                    raise MySchemeError(f"HTTP {e.code} for {url}") from e
                time.sleep(1.5 * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                # ConnectionReset (WinError 10054) is common on this API host.
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise MySchemeError(f"Failed after {self.max_retries} retries: {url}") from last

    def _get_json(self, url: str, api: bool = True) -> dict:
        return json.loads(self._get(url, api=api).decode("utf-8", "ignore"))

    # ------------------------------------------------------------- API key

    def _extract_api_key(self) -> str:
        """
        Pull the current x-api-key from the site's Next.js bundle.

        Strategy: fetch the homepage, find the `_app-<hash>.js` chunk, download
        it, and regex out the 40-char alphanumeric key. Falls back to the
        last-known-good key if anything fails.
        """
        try:
            html = self._get(SITE_BASE + "/search", api=False).decode("utf-8", "ignore")
            chunks = re.findall(r"/_next/static/[^\"']+\.js", html)
            # Prefer the _app chunk (holds global config incl. the key).
            ordered = [c for c in dict.fromkeys(chunks) if "_app" in c] + [
                c for c in dict.fromkeys(chunks) if "_app" not in c
            ]
            for chunk in ordered[:20]:
                try:
                    js = self._get(SITE_BASE + chunk, api=False).decode("utf-8", "ignore")
                except MySchemeError:
                    continue
                if "myscheme" not in js and "x-api-key" not in js:
                    continue
                keys = re.findall(r"[\"']([A-Za-z0-9]{40})[\"']", js)
                if keys:
                    logger.info("Extracted live myScheme API key from %s", chunk)
                    return keys[0]
        except Exception as e:  # noqa: BLE001 — degrade to fallback, never crash boot
            logger.warning("Live API-key extraction failed (%s); using fallback key", e)
        logger.warning("Using last-known-good myScheme API key (may be stale)")
        return FALLBACK_API_KEY

    # ------------------------------------------------------------- Public

    def total_count(self, keyword: str = "") -> int:
        """Return the total number of schemes matching an (optional) keyword."""
        url = (
            f"{API_BASE}/search/v5/schemes?lang=en&q=%5B%5D"
            f"&keyword={quote(keyword)}&sort=&from=0&size=1"
        )
        j = self._get_json(url)
        return int(j["data"]["summary"]["total"])

    def list_page(self, frm: int, size: int, keyword: str = "") -> List[dict]:
        """
        Return one page of scheme summaries.

        Each item's useful fields live under ``item['fields']`` (slug,
        schemeName, briefDescription, schemeCategory, nodalMinistryName, ...).
        """
        url = (
            f"{API_BASE}/search/v5/schemes?lang=en&q=%5B%5D"
            f"&keyword={quote(keyword)}&sort=&from={frm}&size={size}"
        )
        j = self._get_json(url)
        return j["data"]["hits"]["items"]

    def iter_slugs(self, keyword: str = "", page_size: int = 100) -> Iterator[str]:
        """
        Yield every scheme slug, paginating through the full result set.

        Deduplicates slugs (the API can repeat items across pages under load).
        """
        total = self.total_count(keyword)
        logger.info("myScheme reports %d schemes for keyword=%r", total, keyword)
        seen: set[str] = set()
        frm = 0
        while frm < total:
            try:
                items = self.list_page(frm, page_size, keyword=keyword)
            except MySchemeError as e:
                logger.warning("Page from=%d failed (%s); skipping ahead", frm, e)
                frm += page_size
                continue
            if not items:
                break
            for it in items:
                slug = (it.get("fields") or {}).get("slug") or it.get("slug")
                if slug and slug not in seen:
                    seen.add(slug)
                    yield slug
            frm += page_size

    def get_scheme_detail(self, slug: str, lang: str = "en") -> dict:
        """
        Return the full English content tree for a scheme.

        Keys: basicDetails, schemeContent, applicationProcess,
        schemeDefinitions, eligibilityCriteria.
        """
        url = f"{API_BASE}/schemes/v5/public/schemes?slug={quote(slug)}&lang={lang}"
        j = self._get_json(url)
        data = j.get("data") or {}
        content = data.get(lang) or {}
        if not content:
            raise MySchemeError(f"No '{lang}' content for slug={slug}")
        content["_slug"] = slug
        return content
