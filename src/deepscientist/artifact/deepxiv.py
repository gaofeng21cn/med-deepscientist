from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request

from ..network import urlopen_with_proxy as urlopen

DEFAULT_BASE_URL = "https://data.rag.ac.cn"
DEFAULT_RESULT_SIZE = 20
DEFAULT_PREVIEW_CHARACTERS = 5000
DEFAULT_TIMEOUT_SECONDS = 90
USER_AGENT = "DeepScientist/DeepXiv"


def read_deepxiv_content(
    query: str | None,
    *,
    runtime_config: dict[str, Any] | None = None,
    size: int | None = None,
) -> dict[str, Any]:
    normalized_query = str(query or "").strip()
    settings = _resolve_deepxiv_settings(runtime_config)
    if not normalized_query:
        return {
            "ok": False,
            "mode": "retrieve",
            "query": "",
            "error": "DeepXiv query is required.",
            "guidance": "Pass a paper-centric query string to `artifact.deepxiv(query=...)`.",
        }
    if not settings["enabled"]:
        return {
            "ok": False,
            "mode": "retrieve",
            "query": normalized_query,
            "error": "DeepXiv is disabled in this runtime.",
            "guidance": "Enable `config.literature.deepxiv.enabled` before using `artifact.deepxiv(...)`.",
        }
    if not settings["token"]:
        return {
            "ok": False,
            "mode": "retrieve",
            "query": normalized_query,
            "error": "DeepXiv token is missing for this runtime.",
            "guidance": (
                "Set `config.literature.deepxiv.token` or provide the configured token env "
                "before using `artifact.deepxiv(...)`."
            ),
        }

    result_size = settings["default_result_size"] if size is None else max(1, int(size))
    request_url = (
        f"{settings['base_url'].rstrip('/')}/arxiv/?"
        f"{urlencode({'type': 'retrieve', 'query': normalized_query, 'size': str(result_size)})}"
    )
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {settings['token']}",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=settings["request_timeout_seconds"]) as response:  # noqa: S310
            response_text = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "mode": "retrieve",
            "query": normalized_query,
            "result_size": result_size,
            "request_timeout_seconds": settings["request_timeout_seconds"],
            "request_url": request_url,
            "error": str(exc),
            "guidance": "Check the DeepXiv base URL, token, and network reachability, then retry.",
        }

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "mode": "retrieve",
            "query": normalized_query,
            "result_size": result_size,
            "request_timeout_seconds": settings["request_timeout_seconds"],
            "request_url": request_url,
            "error": "DeepXiv returned invalid JSON.",
            "preview": _truncate_text(response_text, settings["preview_characters"]),
            "guidance": "Check the DeepXiv service response format before retrying.",
        }

    raw_results = parsed.get("results") if isinstance(parsed.get("results"), list) else []
    results = [
        _normalize_deepxiv_result(item, rank=index + 1, preview_characters=settings["preview_characters"])
        for index, item in enumerate(raw_results)
    ]
    content = _build_deepxiv_content(
        query=normalized_query,
        result_size=result_size,
        total=parsed.get("total"),
        results=results,
    )
    return {
        "ok": True,
        "mode": "retrieve",
        "source": "deepxiv",
        "query": normalized_query,
        "base_url": settings["base_url"],
        "request_url": request_url,
        "request_timeout_seconds": settings["request_timeout_seconds"],
        "preview_characters": settings["preview_characters"],
        "result_size": result_size,
        "result_count": len(results),
        "total": parsed.get("total"),
        "took": parsed.get("took"),
        "results": results,
        "content": content,
        "preview": _truncate_text(content, settings["preview_characters"]),
        "guidance": "Use the structured `results` payload for shortlist triage, then fall back to `artifact.arxiv(...)` for direct arXiv reads when needed.",
    }


def _resolve_deepxiv_settings(runtime_config: dict[str, Any] | None) -> dict[str, Any]:
    config = runtime_config if isinstance(runtime_config, dict) else {}
    literature = config.get("literature") if isinstance(config.get("literature"), dict) else {}
    deepxiv = literature.get("deepxiv") if isinstance(literature.get("deepxiv"), dict) else {}
    token_env_name = str(deepxiv.get("token_env") or "").strip()
    env_token = str(os.environ.get(token_env_name) or "").strip() if token_env_name else ""
    direct_token = str(deepxiv.get("token") or "").strip()
    return {
        "enabled": bool(deepxiv.get("enabled")),
        "base_url": str(deepxiv.get("base_url") or DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        "token": direct_token or env_token,
        "default_result_size": max(1, int(deepxiv.get("default_result_size") or DEFAULT_RESULT_SIZE)),
        "preview_characters": max(200, int(deepxiv.get("preview_characters") or DEFAULT_PREVIEW_CHARACTERS)),
        "request_timeout_seconds": max(3, int(deepxiv.get("request_timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)),
    }


def _normalize_deepxiv_result(item: Any, *, rank: int, preview_characters: int) -> dict[str, Any]:
    payload = item if isinstance(item, dict) else {}
    abstract = _first_text(payload.get("abstract"), payload.get("summary"), payload.get("content"))
    source_url = _first_text(payload.get("source_url"), payload.get("abs_url"), payload.get("url"), payload.get("paper_url"))
    return {
        "rank": rank,
        "paper_id": _first_text(payload.get("paper_id"), payload.get("arxiv_id"), payload.get("id")),
        "title": _first_text(payload.get("title"), payload.get("paper_title")) or f"DeepXiv result {rank}",
        "authors": _normalize_authors(payload.get("authors")),
        "abstract": abstract or "",
        "abstract_preview": _truncate_text(abstract or "", preview_characters),
        "source_url": source_url,
        "pdf_url": _first_text(payload.get("pdf_url"), payload.get("download_url")),
        "year": payload.get("year"),
        "venue": _first_text(payload.get("venue"), payload.get("journal")),
        "published_at": _first_text(payload.get("published_at"), payload.get("published"), payload.get("publication_date")),
        "doi": _first_text(payload.get("doi")),
        "score": payload.get("score"),
    }


def _normalize_authors(raw_authors: Any) -> list[str]:
    if isinstance(raw_authors, str):
        text = raw_authors.strip()
        return [text] if text else []
    if not isinstance(raw_authors, list):
        return []
    authors: list[str] = []
    for item in raw_authors:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = _first_text(item.get("name"), item.get("author"), item.get("display_name"))
        else:
            text = str(item or "").strip()
        if text:
            authors.append(text)
    return authors


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _truncate_text(text: str, limit: int) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[:limit].rstrip()
    return f"{clipped}...[truncated]"


def _build_deepxiv_content(
    *,
    query: str,
    result_size: int,
    total: Any,
    results: list[dict[str, Any]],
) -> str:
    lines = [
        f"# DeepXiv results for `{query}`",
        "",
        f"- requested_size: {result_size}",
        f"- returned_results: {len(results)}",
        f"- total_results: {total if total is not None else len(results)}",
    ]
    if not results:
        lines.extend(["", "No DeepXiv results were returned for this query."])
        return "\n".join(lines)
    for item in results:
        lines.extend(
            [
                "",
                f"## {item['rank']}. {item['title']}",
                f"- paper_id: {item.get('paper_id') or 'unknown'}",
                f"- authors: {', '.join(item.get('authors') or []) or 'unknown'}",
                f"- source_url: {item.get('source_url') or 'unknown'}",
                f"- pdf_url: {item.get('pdf_url') or 'unknown'}",
            ]
        )
        abstract_preview = str(item.get("abstract_preview") or "").strip()
        if abstract_preview:
            lines.extend(["", abstract_preview])
    return "\n".join(lines)
