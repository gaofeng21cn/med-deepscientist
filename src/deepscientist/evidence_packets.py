from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .shared import ensure_dir, read_json, utc_now, write_json

DEFAULT_EVIDENCE_PACKET_THRESHOLD_BYTES = 48_000
DEFAULT_RUNNER_TOOL_RESULT_THRESHOLD_BYTES = 8_000
_MAX_SUMMARY_CHARS = 900
_MAX_BLOCKERS = 12
_MAX_ITEMS = 12
_SURFACE_CACHE_SCHEMA_VERSION = 1
_READ_CACHE_SCHEMA_VERSION = 1
_HOT_TOOL_RESULT_THRESHOLDS_BYTES = {
    "artifact.get_quest_state": 4_000,
    "artifact.get_global_status": 4_000,
    "artifact.get_paper_contract_health": 4_000,
    "artifact.validate_manuscript_coverage": 4_000,
    "artifact.list_paper_outlines": 2_000,
    "artifact.resolve_runtime_refs": 4_000,
    "artifact.read_quest_documents": 4_000,
    "bash_exec.bash_exec": 2_000,
}
_FULL_DETAIL_FORCE_COMPACT_TOOLS = {
    "artifact.get_quest_state",
    "artifact.get_global_status",
    "artifact.get_paper_contract_health",
    "artifact.validate_manuscript_coverage",
    "artifact.list_paper_outlines",
    "artifact.resolve_runtime_refs",
    "artifact.read_quest_documents",
}


def payload_json_bytes(payload: Any) -> bytes:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        return str(payload).encode("utf-8", errors="replace")


def payload_sha256(payload: Any) -> str:
    return hashlib.sha256(payload_json_bytes(payload)).hexdigest()


def _normalized_tool_name(tool_name: str | None) -> str:
    return str(tool_name or "").strip()


def _compact_threshold_for_tool(tool_name: str, *, default_threshold: int) -> int:
    normalized = _normalized_tool_name(tool_name)
    hot_threshold = _HOT_TOOL_RESULT_THRESHOLDS_BYTES.get(normalized)
    if hot_threshold is None:
        return int(default_threshold)
    return min(int(default_threshold), hot_threshold)


def _tool_force_compaction(
    *,
    tool_name: str,
    full_detail_requested: bool | None,
    force: bool,
) -> bool:
    if force:
        return True
    return bool(full_detail_requested) and _normalized_tool_name(tool_name) in _FULL_DETAIL_FORCE_COMPACT_TOOLS


def _safe_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip())
    return normalized.strip("-")[:80] or "payload"


def _strip_read_cache_volatile(value: Any) -> Any:
    volatile_keys = {
        "created_at",
        "updated_at",
        "generated_at",
        "completed_at",
        "read_cache",
        "run_age_seconds",
        "status_age_seconds",
        "silent_seconds",
        "progress_age_seconds",
        "signal_age_seconds",
    }
    if isinstance(value, dict):
        return {
            key: _strip_read_cache_volatile(item)
            for key, item in value.items()
            if str(key) not in volatile_keys and not str(key).endswith("_age_seconds")
        }
    if isinstance(value, list):
        return [_strip_read_cache_volatile(item) for item in value]
    return value


def _read_cache_path(
    *,
    quest_root: Path,
    tool_name: str,
    detail: str | None,
    cache_key: Any,
) -> Path:
    key_hash = payload_sha256({"tool_name": tool_name, "detail": detail, "cache_key": cache_key})[:20]
    return quest_root / ".ds" / "read_cache" / f"{_slug(tool_name)}-{key_hash}.json"


def _sidecar_path(
    *,
    quest_root: Path,
    run_id: str | None,
    tool_name: str,
    payload_hash: str,
    item_id: str | None = None,
) -> Path:
    run_segment = _slug(run_id or "manual")
    item_segment = _slug(item_id or payload_hash[:12])
    tool_segment = _slug(tool_name)
    return quest_root / ".ds" / "evidence_packets" / run_segment / f"{tool_segment}-{item_segment}.json"


def _collect_blockers(value: Any, blockers: list[str]) -> None:
    if len(blockers) >= _MAX_BLOCKERS:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key or "").lower()
            if any(marker in lowered for marker in ("block", "gap", "missing", "error", "invalid", "unresolved")):
                if isinstance(item, str) and item.strip():
                    blockers.append(item.strip())
                elif isinstance(item, list):
                    for child in item:
                        if len(blockers) >= _MAX_BLOCKERS:
                            break
                        if isinstance(child, str) and child.strip():
                            blockers.append(child.strip())
                        elif isinstance(child, dict):
                            title = str(child.get("title") or child.get("summary") or child.get("reason") or "").strip()
                            status = str(child.get("status") or "").strip()
                            if title:
                                blockers.append(f"{status}: {title}".strip(": "))
                elif isinstance(item, dict):
                    title = str(item.get("title") or item.get("summary") or item.get("reason") or "").strip()
                    if title:
                        blockers.append(title)
            if isinstance(item, (dict, list)):
                _collect_blockers(item, blockers)
            if len(blockers) >= _MAX_BLOCKERS:
                break
    elif isinstance(value, list):
        for item in value:
            _collect_blockers(item, blockers)
            if len(blockers) >= _MAX_BLOCKERS:
                break


def extract_key_blockers(payload: Any) -> list[str]:
    blockers: list[str] = []
    _collect_blockers(payload, blockers)
    seen: set[str] = set()
    ordered: list[str] = []
    for blocker in blockers:
        text = " ".join(str(blocker).split())
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text[:240])
        if len(ordered) >= _MAX_BLOCKERS:
            break
    return ordered


def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return None


def summarize_payload(payload: Any, *, tool_name: str) -> str:
    if not isinstance(payload, dict):
        text = str(payload).strip()
        return (text[: _MAX_SUMMARY_CHARS - 1].rstrip() + "…") if len(text) > _MAX_SUMMARY_CHARS else text

    parts: list[str] = []
    ok_value = payload.get("ok")
    if isinstance(ok_value, bool):
        parts.append(f"ok={ok_value}")
    detail = _first_text(payload, ("detail", "status", "overall_status", "package_status"))
    if detail:
        parts.append(f"detail={detail}")

    quest_state = payload.get("quest_state") if isinstance(payload.get("quest_state"), dict) else {}
    if quest_state:
        for key in ("active_anchor", "runtime_status", "display_status", "continuation_policy", "active_paper_line_ref"):
            value = quest_state.get(key)
            if value is not None:
                parts.append(f"{key}={value}")

    paper_health = payload.get("paper_contract_health")
    if isinstance(paper_health, dict):
        for key in ("writing_ready", "audit_package_ready", "finalize_ready", "recommended_next_stage", "recommended_action"):
            if key in paper_health:
                parts.append(f"{key}={paper_health.get(key)}")
    elif isinstance(quest_state.get("paper_contract_health"), dict):
        nested = quest_state["paper_contract_health"]
        for key in ("writing_ready", "recommended_next_stage", "recommended_action"):
            if key in nested:
                parts.append(f"{key}={nested.get(key)}")

    if "count" in payload:
        parts.append(f"count={payload.get('count')}")
    if "log_line_count" in payload:
        parts.append(f"log_line_count={payload.get('log_line_count')}")
    if "status_counts" in payload and isinstance(payload.get("status_counts"), dict):
        parts.append(f"status_counts={payload.get('status_counts')}")

    blockers = extract_key_blockers(payload)
    if blockers:
        parts.append(f"key_blockers={len(blockers)}")
        parts.append(f"first_blocker={blockers[0]}")

    summary = f"{tool_name}: " + "; ".join(str(part) for part in parts if str(part).strip())
    if summary.strip() == f"{tool_name}:":
        summary = f"{tool_name}: compact evidence packet available in sidecar."
    if len(summary) > _MAX_SUMMARY_CHARS:
        summary = summary[: _MAX_SUMMARY_CHARS - 1].rstrip() + "…"
    return summary


def compact_evidence_payload(
    payload: Any,
    *,
    quest_root: Path,
    run_id: str | None,
    tool_name: str,
    detail: str | None = None,
    item_id: str | None = None,
    force: bool = False,
    threshold_bytes: int = DEFAULT_EVIDENCE_PACKET_THRESHOLD_BYTES,
    reason: str | None = None,
    full_detail_requested: bool | None = None,
) -> tuple[Any, dict[str, Any]]:
    payload_bytes = len(payload_json_bytes(payload))
    if not force and payload_bytes <= max(1, int(threshold_bytes)):
        return payload, {
            "compacted": False,
            "payload_bytes": payload_bytes,
            "threshold_bytes": int(threshold_bytes),
        }

    digest = payload_sha256(payload)
    sidecar_path = _sidecar_path(
        quest_root=quest_root,
        run_id=run_id,
        tool_name=tool_name,
        payload_hash=digest,
        item_id=item_id,
    )
    ensure_dir(sidecar_path.parent)
    key_blockers = extract_key_blockers(payload)
    summary = summarize_payload(payload, tool_name=tool_name)
    write_json(
        sidecar_path,
        {
            "version": 1,
            "created_at": utc_now(),
            "tool_name": tool_name,
            "detail": detail,
            "summary": summary,
            "key_blockers": key_blockers,
            "payload_sha256": digest,
            "payload_bytes": payload_bytes,
            "payload": payload,
        },
    )
    index_path = sidecar_path.parent / "index.json"
    existing_index = read_json(index_path, {})
    existing_items = (
        [dict(item) for item in (existing_index.get("items") or []) if isinstance(item, dict)]
        if isinstance(existing_index, dict)
        else []
    )
    entry = {
        "tool_name": tool_name,
        "detail": detail,
        "summary": summary,
        "sidecar_path": str(sidecar_path),
        "payload_sha256": digest,
        "payload_bytes": payload_bytes,
        "key_blockers": key_blockers,
        "created_at": utc_now(),
    }
    write_json(
        index_path,
        {
            "version": 1,
            "updated_at": utc_now(),
            "run_id": run_id,
            "items": [*existing_items, entry][-200:],
        },
    )
    evidence_packet = {
        "version": 1,
        "tool_name": tool_name,
        "detail": detail,
        "summary": summary,
        "sidecar_path": str(sidecar_path),
        "index_path": str(index_path),
        "payload_sha256": digest,
        "payload_bytes": payload_bytes,
        "key_blockers": key_blockers,
        "full_detail_requested": bool(full_detail_requested),
        "compaction_reason": reason or "context_budget",
        "drill_down_rule": "Open sidecar_path only when the compact facts conflict, are ambiguous, or expose a high-risk blocker that requires source inspection.",
    }
    compacted = {
        "ok": bool(payload.get("ok")) if isinstance(payload, dict) and isinstance(payload.get("ok"), bool) else True,
        "compacted": True,
        "evidence_packet": evidence_packet,
    }
    return compacted, {
        "compacted": True,
        "sidecar_path": str(sidecar_path),
        "payload_sha256": digest,
        "payload_bytes": payload_bytes,
        "summary": summary,
        "key_blocker_count": len(key_blockers),
    }


def compact_runner_tool_event(
    event: dict[str, Any],
    *,
    quest_root: Path,
    run_id: str,
    threshold_bytes: int = DEFAULT_RUNNER_TOOL_RESULT_THRESHOLD_BYTES,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if str(event.get("type") or "") != "runner.tool_result":
        return event, {"compacted": False}
    output = str(event.get("output") or "")
    tool_name = _normalized_tool_name(str(event.get("tool_name") or event.get("mcp_tool") or "tool")) or "tool"
    args = str(event.get("args") or "")
    parsed_args = _safe_json_object(args)
    detail = str(parsed_args.get("detail") or "").strip().lower() or None
    full_detail_requested = detail == "full" or ("detail" in args and "full" in args.lower())
    effective_threshold = _compact_threshold_for_tool(tool_name, default_threshold=threshold_bytes)
    force = _tool_force_compaction(
        tool_name=tool_name,
        full_detail_requested=full_detail_requested,
        force=False,
    )
    output_bytes = len(output.encode("utf-8", errors="replace"))
    if not force and output_bytes <= max(1, int(effective_threshold)):
        return event, {
            "compacted": False,
            "output_bytes": output_bytes,
            "threshold_bytes": int(effective_threshold),
        }

    parsed_payload: Any
    try:
        parsed_payload = json.loads(output)
    except json.JSONDecodeError:
        parsed_payload = {"text": output}
    compacted_payload, meta = compact_evidence_payload(
        parsed_payload,
        quest_root=quest_root,
        run_id=run_id,
        tool_name=tool_name,
        item_id=str(event.get("event_id") or event.get("tool_call_id") or ""),
        force=True,
        threshold_bytes=effective_threshold,
        reason="runner_tool_result_context_budget",
        full_detail_requested=full_detail_requested,
    )
    compacted_event = dict(event)
    compacted_output = json.dumps(compacted_payload, ensure_ascii=False, indent=2)
    compacted_event["output"] = compacted_output
    compacted_event["output_bytes"] = output_bytes
    compacted_event["output_sha256"] = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()
    compacted_event["output_compacted"] = True
    compacted_output_bytes = len(compacted_output.encode("utf-8", errors="replace"))
    compacted_event["output_compaction"] = {
        "reason": "runner_tool_result_context_budget",
        "threshold_bytes": int(effective_threshold),
        "original_output_bytes": output_bytes,
        "compacted_output_bytes": compacted_output_bytes,
        "saved_output_bytes": max(0, output_bytes - compacted_output_bytes),
    }
    compacted_event["evidence_packet"] = compacted_payload.get("evidence_packet") if isinstance(compacted_payload, dict) else None
    meta["output_bytes"] = output_bytes
    meta["threshold_bytes"] = int(effective_threshold)
    meta["compacted_output_bytes"] = compacted_output_bytes
    meta["saved_output_bytes"] = max(0, output_bytes - compacted_output_bytes)
    meta["reason"] = "runner_tool_result_context_budget"
    return compacted_event, meta


def compact_mcp_tool_result(
    payload: dict[str, Any],
    *,
    quest_root: Path,
    run_id: str | None,
    tool_name: str,
    detail: str | None = None,
    force: bool = False,
    threshold_bytes: int | None = None,
    reason: str | None = None,
    full_detail_requested: bool | None = None,
) -> dict[str, Any]:
    normalized_detail = str(detail or "").strip().lower() or None
    requested_full_detail = bool(full_detail_requested) or normalized_detail == "full"
    default_threshold = DEFAULT_EVIDENCE_PACKET_THRESHOLD_BYTES if threshold_bytes is None else int(threshold_bytes)
    if requested_full_detail or tool_name in {"artifact.list_paper_outlines", "bash_exec.bash_exec"}:
        effective_threshold = _compact_threshold_for_tool(tool_name, default_threshold=default_threshold)
    else:
        effective_threshold = default_threshold
    compacted, _meta = compact_evidence_payload(
        payload,
        quest_root=quest_root,
        run_id=run_id,
        tool_name=tool_name,
        detail=detail,
        force=_tool_force_compaction(
            tool_name=tool_name,
            full_detail_requested=requested_full_detail,
            force=force,
        ),
        threshold_bytes=effective_threshold,
        reason=reason,
        full_detail_requested=requested_full_detail,
    )
    return compacted if isinstance(compacted, dict) else payload


def cached_compact_mcp_tool_result(
    payload: dict[str, Any],
    *,
    quest_root: Path,
    run_id: str | None,
    tool_name: str,
    detail: str | None = None,
    cache_key: Any = None,
    source_path: Path | None = None,
    force: bool = False,
    threshold_bytes: int | None = None,
    reason: str | None = None,
    full_detail_requested: bool | None = None,
) -> dict[str, Any]:
    normalized_detail = str(detail or "").strip().lower() or None
    resolved_source = source_path.expanduser().resolve() if source_path is not None else None
    source_stat = resolved_source.stat() if resolved_source is not None and resolved_source.exists() else None
    stable_payload = _strip_read_cache_volatile(payload)
    payload_fingerprint = payload_sha256(stable_payload)
    original_bytes = len(payload_json_bytes(payload))
    resolved_cache_key = cache_key if cache_key is not None else {"detail": normalized_detail}
    cache_path = _read_cache_path(
        quest_root=quest_root,
        tool_name=tool_name,
        detail=normalized_detail,
        cache_key=resolved_cache_key,
    )
    cached = read_json(cache_path, {})
    cache_hit = (
        isinstance(cached, dict)
        and int(cached.get("schema_version") or 0) == _READ_CACHE_SCHEMA_VERSION
        and cached.get("payload_fingerprint") == payload_fingerprint
    )
    read_cache = {
        "schema_version": _READ_CACHE_SCHEMA_VERSION,
        "cache_hit": cache_hit,
        "cache_path": str(cache_path),
        "payload_fingerprint": payload_fingerprint,
        "payload_bytes": original_bytes,
        "source_path": str(resolved_source) if resolved_source is not None else None,
        "source_mtime_ns": getattr(source_stat, "st_mtime_ns", None) if source_stat is not None else None,
        "source_size": getattr(source_stat, "st_size", None) if source_stat is not None else None,
    }
    if cache_hit:
        cached_evidence_packet = (
            dict(cached.get("evidence_packet") or {})
            if isinstance(cached.get("evidence_packet"), dict)
            else None
        )
        if cached_evidence_packet is None:
            sidecar_payload, _sidecar_meta = compact_evidence_payload(
                payload,
                quest_root=quest_root,
                run_id=run_id,
                tool_name=tool_name,
                detail=normalized_detail,
                force=True,
                threshold_bytes=1,
                reason="read_cache_sidecar_ref",
                full_detail_requested=full_detail_requested,
            )
            if isinstance(sidecar_payload, dict) and isinstance(sidecar_payload.get("evidence_packet"), dict):
                cached_evidence_packet = dict(sidecar_payload["evidence_packet"])
                cached["evidence_packet"] = cached_evidence_packet
                write_json(cache_path, cached)
        saved_bytes = max(0, original_bytes)
        read_cache["saved_bytes"] = saved_bytes
        if cached_evidence_packet:
            read_cache["sidecar_path"] = cached_evidence_packet.get("sidecar_path")
            read_cache["payload_sha256"] = cached_evidence_packet.get("payload_sha256")
        result = {
            "ok": bool(payload.get("ok")) if isinstance(payload.get("ok"), bool) else True,
            "compacted": True,
            "delta_marker": True,
            "delta_kind": "unchanged_read_cache",
            "tool_name": tool_name,
            "detail": normalized_detail,
            "fingerprint": payload_fingerprint,
            "summary": cached.get("summary") or summarize_payload(payload, tool_name=tool_name),
            "read_cache": read_cache,
            "command_fingerprint": payload.get("command_fingerprint"),
            "cwd": payload.get("cwd"),
        }
        if cached_evidence_packet:
            result["evidence_packet"] = cached_evidence_packet
        return result

    compacted = compact_mcp_tool_result(
        payload,
        quest_root=quest_root,
        run_id=run_id,
        tool_name=tool_name,
        detail=normalized_detail,
        force=force,
        threshold_bytes=threshold_bytes,
        reason=reason,
        full_detail_requested=full_detail_requested,
    )
    evidence_packet = (
        dict(compacted.get("evidence_packet") or {})
        if isinstance(compacted, dict) and isinstance(compacted.get("evidence_packet"), dict)
        else None
    )
    if evidence_packet is None:
        sidecar_payload, _sidecar_meta = compact_evidence_payload(
            payload,
            quest_root=quest_root,
            run_id=run_id,
            tool_name=tool_name,
            detail=normalized_detail,
            force=True,
            threshold_bytes=1,
            reason="read_cache_sidecar_ref",
            full_detail_requested=full_detail_requested,
        )
        if isinstance(sidecar_payload, dict) and isinstance(sidecar_payload.get("evidence_packet"), dict):
            evidence_packet = dict(sidecar_payload["evidence_packet"])
    read_cache["saved_bytes"] = 0
    if evidence_packet:
        read_cache["sidecar_path"] = evidence_packet.get("sidecar_path")
        read_cache["payload_sha256"] = evidence_packet.get("payload_sha256")
    compacted["read_cache"] = read_cache
    if evidence_packet and "evidence_packet" not in compacted:
        compacted["evidence_packet"] = evidence_packet
    ensure_dir(cache_path.parent)
    write_json(
        cache_path,
        {
            "schema_version": _READ_CACHE_SCHEMA_VERSION,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "tool_name": tool_name,
            "detail": normalized_detail,
            "cache_key": resolved_cache_key,
            "payload_fingerprint": payload_fingerprint,
            "payload_bytes": original_bytes,
            "summary": summarize_payload(payload, tool_name=tool_name),
            "source_path": str(resolved_source) if resolved_source is not None else None,
            "source_mtime_ns": getattr(source_stat, "st_mtime_ns", None) if source_stat is not None else None,
            "source_size": getattr(source_stat, "st_size", None) if source_stat is not None else None,
            "evidence_packet": evidence_packet,
        },
    )
    return compacted


def compact_inventory(items: list[dict[str, Any]], *, keep_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for item in items[:_MAX_ITEMS]:
        compacted.append({key: item.get(key) for key in keep_keys if key in item})
    return compacted


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _file_fact(path: Path, *, root: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        return {
            "path": _relative_path(resolved, root),
            "exists": False,
        }
    stat = resolved.stat()
    return {
        "path": _relative_path(resolved, root),
        "exists": True,
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _paper_root(workspace_root: Path) -> Path:
    return workspace_root / "paper" if (workspace_root / "paper").exists() else workspace_root


def _catalog_items(catalog_path: Path, *, key: str) -> list[dict[str, Any]]:
    payload = read_json(catalog_path, {}) if catalog_path.exists() else {}
    raw_items: Any = []
    if isinstance(payload, dict):
        raw_items = payload.get(key) or payload.get("items") or payload.get("entries") or []
    if not isinstance(raw_items, list):
        return []
    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or item.get("figure_id") or item.get("table_id") or index).strip()
        items.append(
            {
                "id": item_id,
                "status": item.get("status"),
                "path": item.get("path") or item.get("output_path") or item.get("source_path"),
                "title": item.get("title") or item.get("caption"),
            }
        )
    return items


def _inventory_for_workspace(*, quest_root: Path, workspace_root: Path) -> dict[str, Any]:
    root = workspace_root.expanduser().resolve()
    paper = _paper_root(root)
    figure_catalog = _first_existing(
        [
            paper / "figure_catalog.json",
            paper / "figures" / "figure_catalog.json",
            paper / "figures" / "catalog.json",
        ]
    )
    table_catalog = _first_existing(
        [
            paper / "table_catalog.json",
            paper / "tables" / "table_catalog.json",
            paper / "tables" / "catalog.json",
        ]
    )
    file_candidates = [
        paper / "manuscript.md",
        paper / "manuscript_submission.md",
        paper / "manuscript.docx",
        paper / "paper.pdf",
        paper / "paper_contract.json",
        paper / "paper_line_state.json",
        paper / "claim_evidence_map.json",
        paper / "display_registry.json",
        paper / "submission_minimal" / "submission_manifest.json",
        paper / "submission_minimal" / "manuscript.docx",
        paper / "submission_minimal" / "paper.pdf",
    ]
    generated_figures = sorted(
        path
        for folder in (paper / "figures" / "generated", paper / "submission_minimal" / "figures")
        if folder.exists()
        for path in folder.iterdir()
        if path.is_file()
    )
    generated_tables = sorted(
        path
        for folder in (paper / "tables" / "generated", paper / "submission_minimal" / "tables")
        if folder.exists()
        for path in folder.iterdir()
        if path.is_file()
    )
    manifest_path = paper / "submission_minimal" / "submission_manifest.json"
    missing_submission_files = [
        item["path"]
        for item in (
            _file_fact(manifest_path, root=root),
            _file_fact(paper / "submission_minimal" / "manuscript.docx", root=root),
            _file_fact(paper / "submission_minimal" / "paper.pdf", root=root),
        )
        if not item["exists"]
    ]
    return {
        "workspace_root": str(root),
        "quest_root": str(quest_root.expanduser().resolve()),
        "paper_root": str(paper),
        "files": [_file_fact(path, root=root) for path in file_candidates],
        "figures": {
            "catalog_path": str(figure_catalog) if figure_catalog is not None else None,
            "catalog_items": compact_inventory(
                _catalog_items(figure_catalog, key="figures") if figure_catalog is not None else [],
                keep_keys=("id", "status", "path", "title"),
            ),
            "generated_count": len(generated_figures),
            "generated_samples": [_relative_path(path, root) for path in generated_figures[:_MAX_ITEMS]],
        },
        "tables": {
            "catalog_path": str(table_catalog) if table_catalog is not None else None,
            "catalog_items": compact_inventory(
                _catalog_items(table_catalog, key="tables") if table_catalog is not None else [],
                keep_keys=("id", "status", "path", "title"),
            ),
            "generated_count": len(generated_tables),
            "generated_samples": [_relative_path(path, root) for path in generated_tables[:_MAX_ITEMS]],
        },
        "submission_minimal": {
            "manifest_path": str(manifest_path) if manifest_path.exists() else None,
            "missing_required_files": missing_submission_files,
            "ready": not missing_submission_files,
        },
    }


def _surface_candidates(*, quest_root: Path, workspace_root: Path) -> dict[str, list[Path]]:
    paper = _paper_root(workspace_root.expanduser().resolve())
    return {
        "publication_gate": [
            quest_root / "artifacts" / "reports" / "publishability_gate" / "latest.json",
            quest_root / "artifacts" / "reports" / "publication_gate" / "latest.json",
        ],
        "medical_publication_surface": [
            quest_root / "artifacts" / "reports" / "medical_publication_surface" / "latest.json",
            quest_root / "artifacts" / "reports" / "medical_reporting_audit" / "latest.json",
            paper / "medical_publication_surface.json",
        ],
        "submission_minimal": [
            paper / "submission_minimal" / "submission_manifest.json",
            paper / "submission_minimal" / "manuscript.docx",
            paper / "submission_minimal" / "paper.pdf",
        ],
        "submission_authority": [
            paper / "review" / "submission_checklist.json",
            paper / "submission_minimal" / "submission_manifest.json",
        ],
        "display_registry": [
            paper / "display_registry.json",
            paper / "figure_catalog.json",
            paper / "figures" / "figure_catalog.json",
            paper / "table_catalog.json",
            paper / "tables" / "table_catalog.json",
        ],
        "medical_story": [
            paper / "medical_story_contract.json",
            paper / "story_contract.json",
            paper / "paper_contract.json",
        ],
        "figure_semantics": [
            paper / "figure_semantics_manifest.json",
            paper / "figures" / "figure_semantics_manifest.json",
            paper / "figure_catalog.json",
            paper / "figures" / "figure_catalog.json",
        ],
        "claim_evidence_map": [
            paper / "claim_evidence_map.json",
        ],
    }


def _surface_cache_payload(
    *,
    quest_root: Path,
    workspace_root: Path,
    surface_id: str,
    paths: list[Path],
) -> dict[str, Any]:
    root = workspace_root.expanduser().resolve()
    file_facts = [_file_fact(path, root=root) for path in paths]
    fingerprint = payload_sha256({"surface_id": surface_id, "files": file_facts})
    cache_path = quest_root / ".ds" / "gate_cache" / f"{surface_id}.json"
    cached = read_json(cache_path, {})
    cache_hit = (
        isinstance(cached, dict)
        and int(cached.get("schema_version") or 0) == _SURFACE_CACHE_SCHEMA_VERSION
        and cached.get("input_fingerprint") == fingerprint
        and isinstance(cached.get("summary"), dict)
    )
    if cache_hit:
        summary = dict(cached.get("summary") or {})
    else:
        existing = [item for item in file_facts if item.get("exists")]
        missing = [item["path"] for item in file_facts if not item.get("exists")]
        if surface_id == "submission_minimal":
            status = "current" if not missing else "incomplete" if existing else "missing"
            key_blockers = [f"{surface_id} missing {len(missing)} required evidence file(s)"] if missing else []
        else:
            status = "current" if existing else "missing"
            key_blockers = [f"{surface_id} missing required evidence"] if not existing else []
        summary = {
            "surface_id": surface_id,
            "status": status,
            "existing_file_count": len(existing),
            "missing_file_count": len(missing),
            "missing_files": missing[:_MAX_ITEMS],
            "primary_ref": existing[0]["path"] if existing else None,
            "key_blockers": key_blockers,
        }
        ensure_dir(cache_path.parent)
        write_json(
            cache_path,
            {
                "schema_version": _SURFACE_CACHE_SCHEMA_VERSION,
                "generated_at": utc_now(),
                "surface_id": surface_id,
                "input_fingerprint": fingerprint,
                "summary": summary,
            },
        )
    return {
        "surface_id": surface_id,
        "input_fingerprint": fingerprint,
        "cache_hit": cache_hit,
        "cache_path": str(cache_path),
        "summary": summary,
        "files": file_facts,
    }


def build_compact_quest_evidence_packet(
    *,
    quest_root: Path,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    resolved_quest_root = quest_root.expanduser().resolve()
    resolved_workspace_root = (workspace_root or quest_root).expanduser().resolve()
    inventory = _inventory_for_workspace(quest_root=resolved_quest_root, workspace_root=resolved_workspace_root)
    surface_cache = {
        surface_id: _surface_cache_payload(
            quest_root=resolved_quest_root,
            workspace_root=resolved_workspace_root,
            surface_id=surface_id,
            paths=paths,
        )
        for surface_id, paths in _surface_candidates(
            quest_root=resolved_quest_root,
            workspace_root=resolved_workspace_root,
        ).items()
    }
    blockers: list[str] = []
    blockers.extend(inventory["submission_minimal"]["missing_required_files"])
    for surface in surface_cache.values():
        blockers.extend(surface.get("summary", {}).get("key_blockers") or [])
    packet = {
        "version": 1,
        "created_at": utc_now(),
        "packet_kind": "compact_quest_evidence",
        "workspace_root": str(resolved_workspace_root),
        "quest_root": str(resolved_quest_root),
        "inventory": inventory,
        "surface_cache": surface_cache,
        "gate_fingerprints": {
            surface_id: surface["input_fingerprint"] for surface_id, surface in surface_cache.items()
        },
        "deterministic_package_repair_hint": {
            "repair_unit_kind": "deterministic_package_surfaces",
            "controller_hint": "combine_once",
            "surface_ids": [
                "submission_authority",
                "display_registry",
                "medical_story",
                "figure_semantics",
            ],
            "surface_fingerprints": {
                surface_id: surface_cache[surface_id]["input_fingerprint"]
                for surface_id in (
                    "submission_authority",
                    "display_registry",
                    "medical_story",
                    "figure_semantics",
                )
                if surface_id in surface_cache
            },
            "owner_boundary": (
                "MDS supplies deterministic package facts only; MAS remains the owner for publication "
                "readiness, medical interpretation, and submission authority."
            ),
        },
        "key_blockers": list(dict.fromkeys(str(item) for item in blockers if str(item).strip()))[:_MAX_BLOCKERS],
        "ai_first_contract": (
            "Controller supplies deterministic facts only. AI remains responsible for medical judgment, "
            "claim boundaries, manuscript prose, and final publication-readiness interpretation."
        ),
        "drill_down_rule": (
            "Open sidecar or source artifacts only when compact facts conflict, are ambiguous, "
            "or expose a high-risk blocker requiring source inspection."
        ),
    }
    packet["packet_sha256"] = payload_sha256(packet)
    return packet


def materialize_compact_quest_evidence_packet(
    *,
    quest_root: Path,
    workspace_root: Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    packet = build_compact_quest_evidence_packet(quest_root=quest_root, workspace_root=workspace_root)
    compacted, _meta = compact_evidence_payload(
        packet,
        quest_root=quest_root,
        run_id=run_id,
        tool_name="artifact.compact_quest_evidence_packet",
        detail="summary",
        item_id="compact-quest-evidence",
        force=True,
        reason="compact_quest_evidence_packet",
        full_detail_requested=False,
    )
    return compacted if isinstance(compacted, dict) else packet
