"""Secure article URL ingestion.

Guards against SSRF: only http(s), DNS resolution checked against private/
reserved ranges, redirect targets re-validated, response size capped, timeout
enforced. Content extraction uses trafilatura with a BeautifulSoup fallback.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from ..core.config import get_settings
from ..core.logging import logger


class UrlFetchError(Exception):
    pass


@dataclass
class FetchedArticle:
    url: str
    final_url: str
    title: str | None
    text: str
    author: str | None
    publish_date: str | None
    site_name: str | None
    extractor: str


def validate_url(url: str) -> str:
    """Validate scheme + resolve host; reject private/reserved addresses."""
    url = (url or "").strip()
    if not url:
        raise UrlFetchError("URL is empty")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlFetchError("Only http and https URLs are supported")
    host = parsed.hostname
    if not host:
        raise UrlFetchError("URL has no host")
    if host.lower() in ("localhost",) or host.endswith(".local") or host.endswith(".internal"):
        raise UrlFetchError("Private or local hosts are not allowed")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise UrlFetchError(f"Could not resolve host: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise UrlFetchError("URL resolves to a private or reserved address")
    return url


def _check_redirect_target(url: str) -> str:
    """Validate each redirect hop (defence against redirect-based SSRF)."""
    return validate_url(url)


def fetch_article(url: str) -> FetchedArticle:
    settings = get_settings()
    url = validate_url(url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; VeritasBot/1.0; +https://veritas.local) "
            "news-analysis"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    final_url = url
    html_text = ""
    try:
        with httpx.Client(
            timeout=settings.fetch_timeout_seconds,
            follow_redirects=False,
            headers=headers,
            max_redirects=0,
        ) as client:
            current = url
            for _hop in range(5):
                resp = client.get(current)
                if resp.is_redirect:
                    location = resp.headers.get("location", "")
                    nxt = urljoin(current, location)
                    nxt = _check_redirect_target(nxt)
                    final_url = nxt
                    current = nxt
                    continue
                if resp.status_code != 200:
                    raise UrlFetchError(f"Upstream returned HTTP {resp.status_code}")
                ctype = resp.headers.get("content-type", "")
                if "text/html" not in ctype and "application/xhtml" not in ctype:
                    raise UrlFetchError(f"Unsupported content type: {ctype or 'unknown'}")
                body = resp.content[: settings.max_fetch_bytes]
                html_text = body.decode(resp.encoding or "utf-8", errors="replace")
                break
            else:
                raise UrlFetchError("Too many redirects")
    except UrlFetchError:
        raise
    except httpx.TimeoutException as exc:
        raise UrlFetchError("Request timed out fetching the article") from exc
    except httpx.HTTPError as exc:
        raise UrlFetchError(f"Network error while fetching article: {exc.__class__.__name__}") from exc

    if not html_text or len(html_text) < 200:
        raise UrlFetchError("Fetched page did not contain enough readable content")

    # --- extraction ---
    title = None
    author = None
    publish_date = None
    site_name = None
    extractor = "none"

    extracted = trafilatura.extract(
        html_text,
        url=final_url,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    meta = trafilatura.extract_metadata(html_text, default_url=final_url)
    if meta:
        title = getattr(meta, "title", None)
        author = getattr(meta, "author", None)
        publish_date = str(getattr(meta, "date", "") or "") or None
        site_name = getattr(meta, "sitename", None)

    text = extracted or ""
    if len(text) < 200:
        # fallback: readability-ish extraction via bs4
        soup = BeautifulSoup(html_text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup.body or soup
        text = main.get_text("\n", strip=True) if main else ""
        extractor = "bs4-fallback"
        if not title:
            t = soup.find("title")
            title = t.get_text(strip=True) if t else None
    else:
        extractor = "trafilatura"

    if len(text) < 100:
        raise UrlFetchError("Could not extract readable article text from the page")

    # drop excessive whitespace lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    text = "\n".join(lines)

    logger.info("Fetched article from %s (%d chars, extractor=%s)", final_url, len(text), extractor)
    return FetchedArticle(
        url=url,
        final_url=final_url,
        title=title,
        text=text[: settings.max_text_length],
        author=author,
        publish_date=publish_date,
        site_name=site_name,
        extractor=extractor,
    )
