"""Official-docs-first lookup tools for BeeChinese agents."""

from __future__ import annotations

import html
import os
import re
import threading
import urllib.parse
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


DOCS_SOURCES: tuple[DocsSource, ...] = (
    DocsSource(
        key="openhands",
        label="OpenHands SDK Docs",
        home_url="https://docs.openhands.dev/sdk/",
        domains=("docs.openhands.dev",),
        sitemap_candidates=("https://docs.openhands.dev/sitemap.xml",),
    ),
    DocsSource(
        key="taro",
        label="Taro Docs",
        home_url="https://docs.taro.zone/",
        domains=("docs.taro.zone",),
        sitemap_candidates=("https://docs.taro.zone/sitemap.xml",),
    ),
    DocsSource(
        key="nextjs",
        label="Next.js Docs",
        home_url="https://nextjs.org/docs",
        domains=("nextjs.org",),
        sitemap_candidates=("https://nextjs.org/sitemap.xml",),
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
    ),
    DocsSource(
        key="fastapi",
        label="FastAPI Docs",
        home_url="https://fastapi.tiangolo.com/",
        domains=("fastapi.tiangolo.com",),
        sitemap_candidates=("https://fastapi.tiangolo.com/sitemap.xml",),
    ),
    DocsSource(
        key="react",
        label="React Docs",
        home_url="https://react.dev/",
        domains=("react.dev",),
        sitemap_candidates=("https://react.dev/sitemap.xml",),
    ),
    DocsSource(
        key="typescript",
        label="TypeScript Docs",
        home_url="https://www.typescriptlang.org/docs/",
        domains=("www.typescriptlang.org", "typescriptlang.org"),
        sitemap_candidates=("https://www.typescriptlang.org/sitemap.xml",),
    ),
    DocsSource(
        key="postgresql",
        label="PostgreSQL Docs",
        home_url="https://www.postgresql.org/docs/",
        domains=("www.postgresql.org", "postgresql.org"),
        sitemap_candidates=("https://www.postgresql.org/sitemap.xml",),
    ),
    DocsSource(
        key="redis",
        label="Redis Docs",
        home_url="https://redis.io/docs/latest/",
        domains=("redis.io",),
        sitemap_candidates=("https://redis.io/sitemap.xml",),
    ),
    DocsSource(
        key="minio",
        label="MinIO Docs",
        home_url="https://min.io/docs/minio/",
        domains=("min.io",),
        sitemap_candidates=("https://min.io/sitemap.xml",),
    ),
)

DOCS_SOURCE_BY_KEY = {source.key: source for source in DOCS_SOURCES}


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


def _tokenize(text: str) -> list[str]:
    return _dedupe([token for group in _token_groups(text) for token in group])


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
        re.sub(r"\s+", " ", _strip_tags(heading)).strip()
        for heading in headings
        if _strip_tags(heading).strip()
    ]
    return cleaned[:8]


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
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": USER_AGENT},
        )
        self._pages_cache: dict[str, list[DocsPage]] = {}
        self._preview_cache: dict[str, PagePreview] = {}
        self._page_title_hints: dict[str, str] = {}
        self._lock = threading.Lock()

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
            urls: list[str] = []
            for sitemap_url in sitemap_urls:
                urls.extend(self._discover_from_candidate(source, sitemap_url))
            return _dedupe(urls)

        if "<urlset" in text or "<sitemapindex" in text:
            return self._parse_sitemap_xml(source, text)

        return []

    def _parse_sitemap_xml(self, source: DocsSource, xml_text: str) -> list[str]:
        root = ET.fromstring(xml_text)
        tag = root.tag.rsplit("}", maxsplit=1)[-1]
        urls: list[str] = []

        if tag == "sitemapindex":
            for location in root.findall(".//{*}loc"):
                sitemap_url = (location.text or "").strip()
                if not sitemap_url:
                    continue
                try:
                    nested = self._client.get(sitemap_url)
                    nested.raise_for_status()
                    urls.extend(self._parse_sitemap_xml(source, nested.text))
                except Exception:
                    continue
        else:
            for location in root.findall(".//{*}loc"):
                url = (location.text or "").strip()
                if url and self._matches_known_domain(url, source.domains):
                    urls.append(url)

        return _dedupe(urls)

    def _discover_from_root_links(self, source: DocsSource) -> list[str]:
        response = self._client.get(source.home_url)
        response.raise_for_status()
        hrefs = re.findall(r'(?is)href=["\'](.*?)["\']', response.text)
        absolute_urls: list[str] = []
        for href in hrefs:
            absolute = urllib.parse.urljoin(source.home_url, href.strip())
            if self._matches_known_domain(absolute, source.domains):
                absolute_urls.append(absolute)
        return _dedupe(absolute_urls)

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
                if title_hint:
                    with self._lock:
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
        return any(domain in netloc for domain in allowed_domains)

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
            score = 0
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

    def _get_preview(self, page: DocsPage, max_chars: int = 1200) -> PagePreview:
        with self._lock:
            cached = self._preview_cache.get(page.url)
            if cached is not None:
                return cached

        response = self._client.get(page.url)
        response.raise_for_status()
        html_text = response.text
        body_text = _strip_tags(html_text)
        excerpt = body_text[:max_chars].strip()
        title = _extract_title(html_text)
        fallback_title = self._page_title_hints.get(page.url, "")
        if fallback_title and title.lower().startswith("documentation | nestjs"):
            title = fallback_title
        preview = PagePreview(
            url=page.url,
            title=title,
            description=_extract_meta_description(html_text),
            headings=_extract_headings(html_text),
            excerpt=excerpt,
        )
        with self._lock:
            self._preview_cache[page.url] = preview
        return preview

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
        rescored_pages: list[tuple[int, DocsPage, PagePreview | None]] = []
        for base_score, page in ranked_pages[: max(action.max_results * 6, 12)]:
            preview: PagePreview | None = None
            total_score = base_score
            try:
                preview = self._get_preview(page)
                total_score += self._score_preview(preview, query_token_groups)
            except Exception:
                preview = None
            rescored_pages.append((total_score, page, preview))

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
            f"Excerpt:\n{preview.excerpt}"
        )
        return DocsFetchObservation.from_text(
            text=text,
            url=action.url,
            source=matched_source.key,
            title=preview.title,
            headings=preview.headings,
            excerpt=preview.excerpt,
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
