"""Official-docs-first lookup tools for BeeChinese agents."""

from __future__ import annotations

import html
import asyncio
import os
import re
import threading
import urllib.parse
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
warnings.simplefilter("ignore", DeprecationWarning)

import httpx
from pydantic import BaseModel, Field

from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolDefinition,
    ToolExecutor,
    register_tool,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.base import BaseConversation
    from openhands.sdk.conversation.state import ConversationState


USER_AGENT = "BeeChineseDocsTool/0.1 (+https://docs.openhands.dev)"
MAX_PARALLEL_FETCHES = 6
MAX_SITEMAP_WORKERS = 6


@dataclass(frozen=True, slots=True)
class DocsSource:
    """Configuration for one preferred documentation source."""

    key: str
    label: str
    home_url: str
    domains: tuple[str, ...]
    sitemap_candidates: tuple[str, ...]
    github_tree_api_url: str | None = None
    github_content_prefix: str | None = None
    github_repository: str | None = None
    github_ref: str | None = None
    preferred_url_fragments: tuple[str, ...] = ()
    discouraged_url_fragments: tuple[str, ...] = ()


DOCS_SOURCES: tuple[DocsSource, ...] = (
    DocsSource(
        key="openhands",
        label="OpenHands SDK Docs",
        home_url="https://docs.openhands.dev/sdk/",
        domains=("docs.openhands.dev",),
        sitemap_candidates=("https://docs.openhands.dev/sitemap.xml",),
        preferred_url_fragments=("/sdk/", "/api-reference/"),
    ),
    DocsSource(
        key="taro",
        label="Taro Docs",
        home_url="https://docs.taro.zone/",
        domains=("docs.taro.zone",),
        sitemap_candidates=("https://docs.taro.zone/sitemap.xml",),
        preferred_url_fragments=("/docs/",),
    ),
    DocsSource(
        key="nextjs",
        label="Next.js Docs",
        home_url="https://nextjs.org/docs",
        domains=("nextjs.org",),
        sitemap_candidates=("https://nextjs.org/sitemap.xml",),
        preferred_url_fragments=("/docs/",),
    ),
    DocsSource(
        key="nestjs",
        label="NestJS Docs",
        home_url="https://docs.nestjs.com/",
        domains=("docs.nestjs.com",),
        sitemap_candidates=(
            "https://docs.nestjs.com/sitemap.xml",
            "https://docs.nestjs.com/sitemap-index.xml",
            "https://docs.nestjs.com/robots.txt",
        ),
        github_tree_api_url=(
            "https://api.github.com/repos/nestjs/docs.nestjs.com/git/trees/master"
            "?recursive=1"
        ),
        github_content_prefix="content/",
        github_repository="nestjs/docs.nestjs.com",
        github_ref="master",
        preferred_url_fragments=(
            "/techniques/",
            "/fundamentals/",
            "/controllers",
            "/providers",
            "/modules",
            "/pipes",
        ),
    ),
    DocsSource(
        key="fastapi",
        label="FastAPI Docs",
        home_url="https://fastapi.tiangolo.com/",
        domains=("fastapi.tiangolo.com",),
        sitemap_candidates=("https://fastapi.tiangolo.com/sitemap.xml",),
        preferred_url_fragments=("/tutorial/", "/advanced/", "/reference/"),
    ),
    DocsSource(
        key="react",
        label="React Docs",
        home_url="https://react.dev/",
        domains=("react.dev",),
        sitemap_candidates=("https://react.dev/robots.txt",),
        github_tree_api_url=(
            "https://api.github.com/repos/reactjs/react.dev/git/trees/main"
            "?recursive=1"
        ),
        github_content_prefix="src/content/",
        github_repository="reactjs/react.dev",
        github_ref="main",
        preferred_url_fragments=("/reference/", "/learn/"),
        discouraged_url_fragments=("/blog/",),
    ),
    DocsSource(
        key="typescript",
        label="TypeScript Docs",
        home_url="https://www.typescriptlang.org/docs/",
        domains=("www.typescriptlang.org", "typescriptlang.org"),
        sitemap_candidates=("https://www.typescriptlang.org/sitemap.xml",),
        preferred_url_fragments=("/docs/",),
    ),
    DocsSource(
        key="postgresql",
        label="PostgreSQL Docs",
        home_url="https://www.postgresql.org/docs/",
        domains=("www.postgresql.org", "postgresql.org"),
        sitemap_candidates=("https://www.postgresql.org/sitemap.xml",),
        preferred_url_fragments=("/docs/",),
    ),
    DocsSource(
        key="redis",
        label="Redis Docs",
        home_url="https://redis.io/docs/latest/",
        domains=("redis.io",),
        sitemap_candidates=("https://redis.io/sitemap.xml",),
        preferred_url_fragments=("/docs/", "/commands/", "/develop/"),
        discouraged_url_fragments=(
            "/blog/",
            "/glossary/",
            "/resources/",
            "/company/",
            "/solutions/",
            "/compare/",
            "/pricing/",
            "/events/",
        ),
    ),
    DocsSource(
        key="minio",
        label="MinIO Docs",
        home_url="https://docs.min.io/community/minio-object-store/",
        domains=("docs.min.io",),
        sitemap_candidates=("https://docs.min.io/robots.txt",),
        preferred_url_fragments=(
            "/community/minio-object-store/",
            "/community/minio-kes/",
            "/community/minio-directpv/",
            "/enterprise/aistor-object-store/",
        ),
    ),
)

DOCS_SOURCE_BY_KEY = {source.key: source for source in DOCS_SOURCES}

BAD_ASSET_EXTENSIONS = (
    ".css",
    ".js",
    ".mjs",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".mp4",
    ".mp3",
    ".webm",
    ".txt",
    ".xml",
    ".json",
    ".webmanifest",
    ".rss",
)

NOISY_PREFIXES = (
    "skip to main content",
    "openhands docs home page",
    "search...",
    "navigation",
)

NOISY_INLINE_PHRASES = (
    "copy page",
    "ask ai",
)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result


def _token_groups(text: str) -> list[list[str]]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    raw_tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", expanded.lower())
        if token and len(token) >= 2
    ]
    groups: list[list[str]] = []
    for token in raw_tokens:
        groups.append(_token_variants(token))
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    if len(compact) >= 4:
        groups.append([compact])
    return groups


def _token_variants(token: str) -> list[str]:
    variants = [token]
    if len(token) >= 4:
        if token.endswith("ies"):
            variants.append(token[:-3] + "y")
        if token.endswith("y"):
            variants.append(token[:-1] + "ies")
        if token.endswith("es"):
            variants.append(token[:-2])
        if token.endswith("s"):
            variants.append(token[:-1])
        else:
            variants.append(token + "s")
        if token.endswith("ing") and len(token) > 5:
            variants.append(token[:-3])
    return _dedupe([value for value in variants if len(value) >= 2])


def _strip_tags(html_text: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html_text)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    return re.sub(r"\s+", " ", html.unescape(cleaned)).strip()


def _extract_primary_html(html_text: str) -> str:
    patterns = (
        r"(?is)<main\b[^>]*>(.*?)</main>",
        r"(?is)<article\b[^>]*>(.*?)</article>",
        r'(?is)<div\b[^>]*role=["\']main["\'][^>]*>(.*?)</div>',
    )
    best_match = ""
    for pattern in patterns:
        matches = re.findall(pattern, html_text)
        if not matches:
            continue
        candidate = max(matches, key=len)
        if len(candidate) > len(best_match):
            best_match = candidate
    return best_match or html_text


def _extract_title(html_text: str) -> str:
    match = re.search(r"(?is)<title>(.*?)</title>", html_text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()


def _extract_meta_description(html_text: str) -> str:
    patterns = (
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html_text)
        if match:
            return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    return ""


def _extract_headings(html_text: str) -> list[str]:
    headings = re.findall(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", html_text)
    cleaned = [
        re.sub(r"\s+", " ", _strip_tags(heading))
        .replace("\u200b", "")
        .replace("¶", "")
        .strip()
        for heading in headings
        if _strip_tags(heading).strip()
    ]
    return cleaned[:8]


def _extract_markdown_headings(markdown_text: str) -> list[str]:
    headings = []
    for line in markdown_text.splitlines():
        match = re.match(r"^\s{0,3}#{1,3}\s+(.*)$", line)
        if not match:
            continue
        heading = re.sub(r"\s+", " ", match.group(1)).strip()
        heading = re.sub(r"\{#.*?\}$", "", heading).strip()
        heading = re.sub(r"\{\/\*.*?\*\/\}", "", heading).strip()
        heading = heading.replace("`", "").strip()
        if heading:
            headings.append(heading)
    return _dedupe(headings)[:8]


def _extract_frontmatter_title(markdown_text: str) -> str:
    match = re.match(r"(?ms)^---\s*\n(.*?)\n---\s*\n", markdown_text)
    if not match:
        return ""
    frontmatter = match.group(1)
    title_match = re.search(r'(?im)^title:\s*["\']?(.*?)["\']?\s*$', frontmatter)
    if not title_match:
        return ""
    return re.sub(r"\s+", " ", title_match.group(1)).strip()


def _strip_markdown(markdown_text: str) -> str:
    text = markdown_text
    text = re.sub(r"(?ms)^---\s*\n.*?\n---\s*\n", "", text)
    text = re.sub(r"(?ms)^```.*?^```", " ", text)
    text = re.sub(r"\{\/\*.*?\*\/\}", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_excerpt(text: str, anchor: str = "") -> str:
    cleaned = re.sub(r"\s+", " ", text).replace("\u200b", "").strip()
    lowered = cleaned.lower()
    for prefix in NOISY_PREFIXES:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip(" :-")
            lowered = cleaned.lower()
    for phrase in NOISY_INLINE_PHRASES:
        cleaned = re.sub(rf"(?i)\b{re.escape(phrase)}\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    lowered = cleaned.lower()
    if anchor:
        anchor_index = lowered.find(anchor.lower())
        if anchor_index > 0:
            cleaned = cleaned[anchor_index:]
    return cleaned


def _score_text_match(
    text: str,
    query_token_groups: list[list[str]],
    *,
    whole_word_points: int,
    substring_points: int,
) -> int:
    if not text.strip():
        return 0

    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    padded = f" {normalized} "
    score = 0
    for index, token_group in enumerate(query_token_groups):
        group_score = 0
        for token in token_group:
            if f" {token} " in padded:
                group_score = max(group_score, whole_word_points)
            elif token in compact:
                group_score = max(group_score, substring_points)
        if group_score > 0:
            group_score += max(0, 2 - index)
        score += group_score
    return score


@dataclass(slots=True)
class DocsPage:
    """A candidate docs page discovered from a preferred source."""

    source_key: str
    url: str


@dataclass(slots=True)
class PagePreview:
    """Lightweight extracted metadata for a docs page."""

    url: str
    title: str
    description: str
    headings: list[str]
    excerpt: str


class DocsSearchResult(BaseModel):
    """A ranked docs result returned to the agent."""

    source: str = Field(description="Source key, for example 'openhands'")
    source_label: str = Field(description="Human-readable source label")
    url: str = Field(description="Preferred docs URL")
    title: str = Field(description="Page title when available")
    snippet: str = Field(description="Description or excerpt")
    score: int = Field(description="Internal relevance score")


class DocsSearchAction(Action):
    """Search preferred documentation sources."""

    query: str = Field(description="Documentation topic, API name, or concept to search")
    framework: str | None = Field(
        default=None,
        description=(
            "Optional preferred source key, such as openhands, taro, nextjs, nestjs, "
            "fastapi, react, typescript, postgresql, redis, or minio"
        ),
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of ranked docs results to return",
    )


class DocsFetchAction(Action):
    """Fetch and summarize one preferred docs page."""

    url: str = Field(description="Absolute docs URL discovered from docs_search or known official docs")
    max_chars: int = Field(
        default=3000,
        ge=500,
        le=8000,
        description="Maximum number of body characters to return in the excerpt",
    )


class DocsSearchObservation(Observation):
    """Observation returned by docs_search."""

    query: str = Field(description="Original query")
    searched_sources: list[str] = Field(description="Source keys actually searched")
    results: list[DocsSearchResult] = Field(
        default_factory=list,
        description="Ranked docs results",
    )


class DocsFetchObservation(Observation):
    """Observation returned by docs_fetch."""

    url: str = Field(description="Fetched URL")
    source: str = Field(description="Matched source key")
    title: str = Field(description="Extracted page title")
    headings: list[str] = Field(default_factory=list, description="Top headings from the page")
    excerpt: str = Field(description="Extracted body excerpt")


class DocsToolExecutor(ToolExecutor[DocsSearchAction | DocsFetchAction, Observation]):
    """Executor that prefers official documentation sitemaps and caches results."""

    def __init__(self) -> None:
        self._client_kwargs = {
            "follow_redirects": True,
            "timeout": 20.0,
            "headers": {"User-Agent": USER_AGENT},
            "limits": httpx.Limits(max_keepalive_connections=12, max_connections=24),
        }
        self._client = httpx.Client(**self._client_kwargs)
        self._pages_cache: dict[str, list[DocsPage]] = {}
        self._preview_cache: dict[str, PagePreview] = {}
        self._page_title_hints: dict[str, str] = {}
        self._github_markdown_paths: dict[str, str] = {}
        self._lock = threading.Lock()

    def _new_async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(**self._client_kwargs)

    def _run_async(self, coroutine: Any) -> object:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coroutine)).result()

    def __call__(
        self,
        action: DocsSearchAction | DocsFetchAction,
        conversation: "BaseConversation | None" = None,  # noqa: ARG002
    ) -> Observation:
        if isinstance(action, DocsSearchAction):
            return self.search(action)
        return self.fetch(action)

    def _candidate_sources(self, framework: str | None) -> list[DocsSource]:
        if framework:
            requested = DOCS_SOURCE_BY_KEY.get(framework.strip().lower())
            if requested is not None:
                return [requested]
        return list(DOCS_SOURCES)

    def _get_pages_for_source(self, source: DocsSource) -> list[DocsPage]:
        with self._lock:
            cached = self._pages_cache.get(source.key)
            if cached is not None:
                return cached

        urls = self._discover_source_urls(source)
        pages = [DocsPage(source_key=source.key, url=url) for url in urls]
        with self._lock:
            self._pages_cache[source.key] = pages
        return pages

    def _discover_source_urls(self, source: DocsSource) -> list[str]:
        discovered: list[str] = []
        for candidate in source.sitemap_candidates:
            try:
                discovered = self._discover_from_candidate(source, candidate)
            except Exception:
                discovered = []
            if discovered:
                return discovered

        if source.github_tree_api_url and source.github_content_prefix:
            try:
                discovered = self._discover_from_github_tree(source)
            except Exception:
                discovered = []
            if discovered:
                return discovered

        return self._discover_from_root_links(source)

    def _discover_from_candidate(self, source: DocsSource, candidate_url: str) -> list[str]:
        response = self._client.get(candidate_url)
        response.raise_for_status()
        text = response.text

        if candidate_url.endswith("robots.txt"):
            sitemap_urls = re.findall(r"(?im)^Sitemap:\s*(\S+)\s*$", text)
            return self._run_async(
                self._async_discover_from_sitemap_urls(source, sitemap_urls)
            )

        if "<urlset" in text or "<sitemapindex" in text:
            return self._parse_sitemap_xml(source, text)

        return []

    def _parse_sitemap_xml(self, source: DocsSource, xml_text: str) -> list[str]:
        root = ET.fromstring(xml_text)
        tag = root.tag.rsplit("}", maxsplit=1)[-1]
        urls: list[str] = []

        if tag == "sitemapindex":
            sitemap_urls = [
                (location.text or "").strip()
                for location in root.findall(".//{*}loc")
                if (location.text or "").strip()
            ]
            if not sitemap_urls:
                return []

            with ThreadPoolExecutor(
                max_workers=min(MAX_SITEMAP_WORKERS, len(sitemap_urls))
            ) as executor:
                futures = {
                    executor.submit(self._fetch_and_parse_nested_sitemap, source, sitemap_url): sitemap_url
                    for sitemap_url in sitemap_urls
                }
                for future in as_completed(futures):
                    try:
                        urls.extend(future.result())
                    except Exception:
                        continue
        else:
            for location in root.findall(".//{*}loc"):
                url = (location.text or "").strip()
                if url and self._is_supported_docs_url(url, source):
                    urls.append(url)

        return _dedupe(urls)

    def _discover_from_root_links(self, source: DocsSource) -> list[str]:
        response = self._client.get(source.home_url)
        response.raise_for_status()
        hrefs = re.findall(r'(?is)href=["\'](.*?)["\']', response.text)
        absolute_urls: list[str] = []
        for href in hrefs:
            absolute = urllib.parse.urljoin(source.home_url, href.strip())
            if self._is_supported_docs_url(absolute, source):
                absolute_urls.append(absolute)
        return _dedupe(absolute_urls)

    def _fetch_and_parse_nested_sitemap(
        self,
        source: DocsSource,
        sitemap_url: str,
    ) -> list[str]:
        nested = self._client.get(sitemap_url)
        nested.raise_for_status()
        return self._parse_sitemap_xml(source, nested.text)

    async def _async_discover_from_sitemap_urls(
        self,
        source: DocsSource,
        sitemap_urls: list[str],
    ) -> list[str]:
        if not sitemap_urls:
            return []

        async with self._new_async_client() as client:
            semaphore = asyncio.Semaphore(MAX_SITEMAP_WORKERS)

            async def collect(sitemap_url: str) -> list[str]:
                try:
                    async with semaphore:
                        response = await client.get(sitemap_url)
                    response.raise_for_status()
                except Exception:
                    return []

                text = response.text
                if "<urlset" in text or "<sitemapindex" in text:
                    return self._parse_sitemap_xml(source, text)
                return []

            nested_results = await asyncio.gather(
                *(collect(sitemap_url) for sitemap_url in sitemap_urls)
            )

        urls: list[str] = []
        for result in nested_results:
            urls.extend(result)
        return _dedupe(urls)

    def _discover_from_github_tree(self, source: DocsSource) -> list[str]:
        if not source.github_tree_api_url or not source.github_content_prefix:
            return []

        response = self._client.get(source.github_tree_api_url)
        response.raise_for_status()
        payload = response.json()
        tree = payload.get("tree", [])
        urls: list[str] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = str(item.get("path", "")).strip()
            url = self._docs_url_from_github_path(source, path)
            if url:
                title_hint = self._title_hint_from_github_path(source, path)
                with self._lock:
                    self._github_markdown_paths[url] = path
                    if title_hint:
                        self._page_title_hints[url] = title_hint
                urls.append(url)
        return _dedupe(urls)

    def _docs_url_from_github_path(self, source: DocsSource, path: str) -> str | None:
        prefix = source.github_content_prefix
        if not prefix or not path.startswith(prefix) or not path.endswith(".md"):
            return None

        relative = path[len(prefix) : -3].strip("/")
        if not relative or relative.endswith("/index"):
            relative = relative.removesuffix("/index")

        return urllib.parse.urljoin(source.home_url, relative)

    def _title_hint_from_github_path(self, source: DocsSource, path: str) -> str:
        prefix = source.github_content_prefix
        if not prefix or not path.startswith(prefix) or not path.endswith(".md"):
            return ""

        relative = path[len(prefix) : -3].strip("/")
        if not relative:
            return ""

        parts = [segment.replace("-", " ").title() for segment in relative.split("/")]
        return " / ".join(parts)

    def _matches_known_domain(self, url: str, allowed_domains: tuple[str, ...]) -> bool:
        try:
            netloc = urllib.parse.urlparse(url).netloc.lower()
        except Exception:
            return False
        return any(netloc == domain or netloc.endswith("." + domain) for domain in allowed_domains)

    def _is_supported_docs_url(self, url: str, source: DocsSource) -> bool:
        if not self._matches_known_domain(url, source.domains):
            return False

        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        if any(path.endswith(extension) for extension in BAD_ASSET_EXTENSIONS):
            return False
        if parsed.scheme not in {"http", "https"}:
            return False
        return True

    def _page_path_weight(self, page: DocsPage) -> int:
        source = DOCS_SOURCE_BY_KEY[page.source_key]
        normalized = page.url.lower()
        score = 0
        for fragment in source.preferred_url_fragments:
            if fragment.lower() in normalized:
                score += 4
        for fragment in source.discouraged_url_fragments:
            if fragment.lower() in normalized:
                score -= 5
        return score

    def _markdown_raw_url(self, source: DocsSource, path: str) -> str:
        if not source.github_repository or not source.github_ref:
            raise ValueError("GitHub repository metadata is not configured.")
        quoted_path = "/".join(urllib.parse.quote(part) for part in path.split("/"))
        return (
            f"https://raw.githubusercontent.com/"
            f"{source.github_repository}/{source.github_ref}/{quoted_path}"
        )

    def _github_path_from_docs_url(self, source: DocsSource, url: str) -> str | None:
        prefix = source.github_content_prefix
        if not prefix:
            return None

        parsed = urllib.parse.urlparse(url)
        relative = parsed.path.strip("/")
        if not relative:
            return None

        return f"{prefix}{relative}.md"

    def _rank_pages(
        self,
        pages: list[DocsPage],
        query: str,
        max_results: int,
    ) -> list[tuple[int, DocsPage]]:
        query_token_groups = _token_groups(query)
        ranked: list[tuple[int, DocsPage]] = []
        for page in pages:
            decoded_url = urllib.parse.unquote(page.url).lower()
            compact_url = re.sub(r"[^a-z0-9]+", "", decoded_url)
            score = self._page_path_weight(page)
            for index, token_group in enumerate(query_token_groups):
                group_score = 0
                for token in token_group:
                    if f"/{token}" in decoded_url:
                        group_score = max(group_score, 6)
                    elif token in compact_url:
                        group_score = max(group_score, 5)
                    elif token in decoded_url:
                        group_score = max(group_score, 2)
                if group_score > 0:
                    group_score += max(0, 2 - index)
                score += group_score
            if score > 0:
                ranked.append((score, page))

        ranked.sort(key=lambda item: (-item[0], len(item[1].url)))
        return ranked[: max_results * 4]

    def _score_preview(self, preview: PagePreview, query_token_groups: list[list[str]]) -> int:
        return (
            _score_text_match(
                preview.title,
                query_token_groups,
                whole_word_points=7,
                substring_points=4,
            )
            + _score_text_match(
                " ".join(preview.headings),
                query_token_groups,
                whole_word_points=5,
                substring_points=3,
            )
            + _score_text_match(
                preview.description,
                query_token_groups,
                whole_word_points=3,
                substring_points=2,
            )
        )

    def _build_preview(
        self,
        page: DocsPage,
        *,
        max_chars: int,
        client: httpx.Client,
    ) -> PagePreview:
        source = DOCS_SOURCE_BY_KEY[page.source_key]
        github_path = self._github_markdown_paths.get(page.url) or self._github_path_from_docs_url(
            source,
            page.url,
        )
        if github_path and source.github_repository and source.github_ref:
            try:
                return self._get_preview_from_markdown(
                    source=source,
                    page=page,
                    path=github_path,
                    max_chars=max_chars,
                    client=client,
                )
            except Exception:
                pass

        response = client.get(page.url)
        response.raise_for_status()
        html_text = response.text
        primary_html = _extract_primary_html(html_text)
        heading_match = re.search(r"(?is)<h[1-3][^>]*>", primary_html)
        if heading_match:
            primary_html = primary_html[heading_match.start() :]
        body_text = _strip_tags(primary_html)
        title = _extract_title(html_text)
        fallback_title = self._page_title_hints.get(page.url, "")
        if fallback_title and title.lower().startswith("documentation | nestjs"):
            title = fallback_title
        headings = _extract_headings(primary_html)
        anchor = headings[0] if headings else title
        excerpt = _clean_excerpt(body_text, anchor=anchor)[: max(max_chars, 4000)].strip()
        return PagePreview(
            url=page.url,
            title=title,
            description=_extract_meta_description(html_text),
            headings=headings,
            excerpt=excerpt,
        )

    def _get_preview(self, page: DocsPage, max_chars: int = 1200) -> PagePreview:
        with self._lock:
            cached = self._preview_cache.get(page.url)
            if cached is not None:
                return cached

        preview = self._build_preview(page, max_chars=max_chars, client=self._client)
        with self._lock:
            self._preview_cache[page.url] = preview
        return preview

    def _get_preview_from_markdown(
        self,
        *,
        source: DocsSource,
        page: DocsPage,
        path: str,
        max_chars: int,
        client: httpx.Client,
    ) -> PagePreview:
        response = client.get(self._markdown_raw_url(source, path))
        response.raise_for_status()
        markdown_text = response.text
        headings = _extract_markdown_headings(markdown_text)
        frontmatter_title = _extract_frontmatter_title(markdown_text)
        title = (
            frontmatter_title
            or headings[0]
            or self._page_title_hints.get(page.url, page.url)
        )
        plain_text = _strip_markdown(markdown_text)
        excerpt = _clean_excerpt(plain_text, anchor=title)[: max(max_chars, 4000)].strip()
        return PagePreview(
            url=page.url,
            title=title,
            description="",
            headings=headings,
            excerpt=excerpt,
        )

    async def _async_get_preview_from_markdown(
        self,
        *,
        source: DocsSource,
        page: DocsPage,
        path: str,
        max_chars: int,
        client: httpx.AsyncClient,
    ) -> PagePreview:
        response = await client.get(self._markdown_raw_url(source, path))
        response.raise_for_status()
        markdown_text = response.text
        headings = _extract_markdown_headings(markdown_text)
        frontmatter_title = _extract_frontmatter_title(markdown_text)
        title = (
            frontmatter_title
            or headings[0]
            or self._page_title_hints.get(page.url, page.url)
        )
        plain_text = _strip_markdown(markdown_text)
        excerpt = _clean_excerpt(plain_text, anchor=title)[: max(max_chars, 4000)].strip()
        return PagePreview(
            url=page.url,
            title=title,
            description="",
            headings=headings,
            excerpt=excerpt,
        )

    async def _async_build_preview(
        self,
        page: DocsPage,
        *,
        max_chars: int,
        client: httpx.AsyncClient,
    ) -> PagePreview:
        source = DOCS_SOURCE_BY_KEY[page.source_key]
        github_path = self._github_markdown_paths.get(page.url) or self._github_path_from_docs_url(
            source,
            page.url,
        )
        if github_path and source.github_repository and source.github_ref:
            try:
                return await self._async_get_preview_from_markdown(
                    source=source,
                    page=page,
                    path=github_path,
                    max_chars=max_chars,
                    client=client,
                )
            except Exception:
                pass

        response = await client.get(page.url)
        response.raise_for_status()
        html_text = response.text
        primary_html = _extract_primary_html(html_text)
        heading_match = re.search(r"(?is)<h[1-3][^>]*>", primary_html)
        if heading_match:
            primary_html = primary_html[heading_match.start() :]
        body_text = _strip_tags(primary_html)
        title = _extract_title(html_text)
        fallback_title = self._page_title_hints.get(page.url, "")
        if fallback_title and title.lower().startswith("documentation | nestjs"):
            title = fallback_title
        headings = _extract_headings(primary_html)
        anchor = headings[0] if headings else title
        excerpt = _clean_excerpt(body_text, anchor=anchor)[: max(max_chars, 4000)].strip()
        return PagePreview(
            url=page.url,
            title=title,
            description=_extract_meta_description(html_text),
            headings=headings,
            excerpt=excerpt,
        )

    async def _async_get_preview_with_client(
        self,
        page: DocsPage,
        *,
        client: httpx.AsyncClient,
        max_chars: int = 1200,
    ) -> PagePreview:
        with self._lock:
            cached = self._preview_cache.get(page.url)
            if cached is not None:
                return cached

        preview = await self._async_build_preview(page, max_chars=max_chars, client=client)

        with self._lock:
            cached = self._preview_cache.get(page.url)
            if cached is not None:
                return cached
            self._preview_cache[page.url] = preview
            return preview

    async def _async_rescore_preview_candidates(
        self,
        preview_candidates: list[tuple[int, DocsPage]],
        query_token_groups: list[list[str]],
    ) -> list[tuple[int, DocsPage, PagePreview | None]]:
        if not preview_candidates:
            return []

        async with self._new_async_client() as client:
            semaphore = asyncio.Semaphore(MAX_PARALLEL_FETCHES)

            async def collect_result(
                base_score: int,
                page: DocsPage,
            ) -> tuple[int, DocsPage, PagePreview | None]:
                preview: PagePreview | None = None
                total_score = base_score
                try:
                    async with semaphore:
                        preview = await self._async_get_preview_with_client(
                            page,
                            client=client,
                        )
                    total_score += self._score_preview(preview, query_token_groups)
                except Exception:
                    preview = None
                return total_score, page, preview

            tasks = [
                collect_result(base_score, page)
                for base_score, page in preview_candidates
            ]
            return await asyncio.gather(*tasks)

    def search(self, action: DocsSearchAction) -> DocsSearchObservation:
        sources = self._candidate_sources(action.framework)
        ranked_pages: list[tuple[int, DocsPage]] = []
        for source in sources:
            pages = self._get_pages_for_source(source)
            ranked_pages.extend(
                self._rank_pages(pages=pages, query=action.query, max_results=action.max_results)
            )

        ranked_pages.sort(key=lambda item: (-item[0], len(item[1].url)))
        query_token_groups = _token_groups(action.query)
        preview_budget = max(action.max_results * 2, 6)
        preview_candidates = ranked_pages[:preview_budget]
        rescored_pages = self._run_async(
            self._async_rescore_preview_candidates(
                preview_candidates,
                query_token_groups,
            )
        )

        rescored_pages.sort(key=lambda item: (-item[0], len(item[1].url)))
        rescored_pages = rescored_pages[: action.max_results]

        results: list[DocsSearchResult] = []
        for score, page, preview in rescored_pages:
            source = DOCS_SOURCE_BY_KEY[page.source_key]
            if preview is None:
                snippet = ""
                title = page.url
            else:
                snippet = preview.description or preview.excerpt
                title = preview.title or page.url
            results.append(
                DocsSearchResult(
                    source=source.key,
                    source_label=source.label,
                    url=page.url,
                    title=title,
                    snippet=snippet[:500],
                    score=score,
                )
            )

        if not results:
            searched = ", ".join(source.key for source in sources)
            return DocsSearchObservation.from_text(
                text=(
                    f"No preferred documentation results found for '{action.query}' "
                    f"inside: {searched}. Use browser tools as fallback if needed."
                ),
                query=action.query,
                searched_sources=[source.key for source in sources],
                results=[],
            )

        rendered_results = []
        for index, result in enumerate(results, start=1):
            rendered_results.append(
                f"{index}. [{result.source_label}] {result.title}\n"
                f"URL: {result.url}\n"
                f"Snippet: {result.snippet}\n"
                f"Score: {result.score}"
            )
        return DocsSearchObservation.from_text(
            text=(
                f"Preferred documentation results for '{action.query}':\n"
                + "\n\n".join(rendered_results)
                + "\n\nThese results are ranked from preferred docs domains. "
                "If they are insufficient, browser tools may be used as fallback."
            ),
            query=action.query,
            searched_sources=[source.key for source in sources],
            results=results,
        )

    def fetch(self, action: DocsFetchAction) -> DocsFetchObservation:
        matched_source = next(
            (
                source
                for source in DOCS_SOURCES
                if self._matches_known_domain(action.url, source.domains)
            ),
            None,
        )
        if matched_source is None:
            return DocsFetchObservation.from_text(
                text=(
                    "docs_fetch only accepts known preferred documentation URLs. "
                    "Use browser tools for non-preferred domains."
                ),
                url=action.url,
                source="unknown",
                title="",
                headings=[],
                excerpt="",
                is_error=True,
            )

        preview = self._get_preview(
            DocsPage(source_key=matched_source.key, url=action.url),
            max_chars=action.max_chars,
        )
        text = (
            f"Fetched preferred documentation page from {matched_source.label}\n"
            f"Title: {preview.title or action.url}\n"
            f"URL: {action.url}\n"
            f"Headings: {', '.join(preview.headings) if preview.headings else '(none found)'}\n"
            f"Excerpt:\n{preview.excerpt[: action.max_chars]}"
        )
        return DocsFetchObservation.from_text(
            text=text,
            url=action.url,
            source=matched_source.key,
            title=preview.title,
            headings=preview.headings,
            excerpt=preview.excerpt[: action.max_chars],
        )


DOCS_SEARCH_DESCRIPTION = """Preferred documentation search tool.
* Searches curated framework documentation sources with official-domain priority.
* Works best for OpenHands SDK, Taro, Next.js, NestJS, FastAPI, React, TypeScript, PostgreSQL, Redis, and MinIO.
* Uses preferred documentation source indexes first, which is usually faster and cleaner than generic browser navigation.
* Returns ranked URLs plus short snippets.
* If no result is sufficient, browser tools may still be used as fallback.
"""


DOCS_FETCH_DESCRIPTION = """Preferred documentation fetch tool.
* Fetches and extracts a concise summary from a preferred docs URL.
* Only accepts URLs from known preferred documentation domains.
* Use after docs_search or when you already know the official docs URL.
* Returns title, headings, and a cleaned excerpt.
"""


class DocsSearchTool(ToolDefinition[DocsSearchAction, DocsSearchObservation]):
    """Search preferred documentation sources."""

    @classmethod
    def create(
        cls,
        executor: DocsToolExecutor,
    ) -> Sequence["DocsSearchTool"]:
        return [
            cls(
                description=DOCS_SEARCH_DESCRIPTION,
                action_type=DocsSearchAction,
                observation_type=DocsSearchObservation,
                annotations=ToolAnnotations(
                    title="preferred docs search",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=True,
                ),
                executor=executor,
            )
        ]


class DocsFetchTool(ToolDefinition[DocsFetchAction, DocsFetchObservation]):
    """Fetch one preferred documentation page."""

    @classmethod
    def create(
        cls,
        executor: DocsToolExecutor,
    ) -> Sequence["DocsFetchTool"]:
        return [
            cls(
                description=DOCS_FETCH_DESCRIPTION,
                action_type=DocsFetchAction,
                observation_type=DocsFetchObservation,
                annotations=ToolAnnotations(
                    title="preferred docs fetch",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=True,
                ),
                executor=executor,
            )
        ]


class DocsToolSet(ToolDefinition[Action, Observation]):
    """Tool set exposing fast preferred documentation search and fetch tools."""

    _shared_executor: DocsToolExecutor | None = None
    _lock = threading.Lock()

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState",  # noqa: ARG003
    ) -> Sequence[ToolDefinition]:
        with cls._lock:
            if cls._shared_executor is None:
                cls._shared_executor = DocsToolExecutor()
            executor = cls._shared_executor

        tools: list[ToolDefinition] = []
        tools.extend(DocsSearchTool.create(executor))
        tools.extend(DocsFetchTool.create(executor))
        return tools


register_tool(DocsToolSet.name, DocsToolSet)
