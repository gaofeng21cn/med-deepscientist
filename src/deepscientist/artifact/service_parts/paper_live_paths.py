from __future__ import annotations

import copy
import os
from pathlib import Path, PurePosixPath
from typing import Any


def path_is_within(path: Path, root: Path | None) -> bool:
    if root is None:
        return False
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def rewrite_workspace_legacy_parts(path: Path) -> Path:
    parts = list(path.parts)
    rewritten: list[str] = []
    index = 0
    while index < len(parts):
        if index + 1 < len(parts) and parts[index] == "ops" and parts[index + 1] == "deepscientist":
            rewritten.extend(["ops", "med-deepscientist"])
            index += 2
            continue
        rewritten.append(parts[index])
        index += 1
    return Path(*rewritten) if rewritten else Path()


def collapse_duplicate_paper_segments(path: Path) -> Path:
    parts = list(path.parts)
    collapsed: list[str] = []
    for part in parts:
        if part == "paper" and collapsed and collapsed[-1] == "paper":
            continue
        collapsed.append(part)
    return Path(*collapsed) if collapsed else Path()


def paper_live_path_candidates(
    raw_path: object,
    *,
    source_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> list[Path]:
    text = str(raw_path or "").strip()
    if not text:
        return []
    legacy_roots = [Path(item).expanduser().resolve(strict=False) for item in (legacy_workspace_roots or [])]
    candidate = Path(text).expanduser()
    resolved: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        normalized = path.expanduser().resolve(strict=False)
        key = str(normalized)
        if key in seen:
            return
        seen.add(key)
        resolved.append(normalized)

    if candidate.is_absolute():
        add(candidate)
        if current_workspace_root is not None:
            current_root = current_workspace_root.expanduser().resolve(strict=False)
            try:
                relative = candidate.resolve(strict=False).relative_to(current_root)
            except ValueError:
                relative = None
            if relative is not None:
                add(current_root / rewrite_workspace_legacy_parts(relative))
            for legacy_root in legacy_roots:
                try:
                    legacy_relative = candidate.resolve(strict=False).relative_to(legacy_root)
                except ValueError:
                    continue
                add(current_root / rewrite_workspace_legacy_parts(legacy_relative))
    else:
        collapsed_candidate = collapse_duplicate_paper_segments(candidate)
        if collapsed_candidate != candidate:
            add(source_root / collapsed_candidate)
        add(source_root / candidate)
    return resolved


def normalize_paper_live_path(
    raw_path: object,
    *,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
    target_override: Path | None = None,
) -> str | None:
    text = str(raw_path or "").strip()
    if not text:
        return None
    if target_override is not None:
        return os.path.relpath(target_override, target_root).replace(os.sep, "/")
    candidate_roots = [
        source_root.resolve(strict=False),
        target_root.resolve(strict=False),
        current_workspace_root.expanduser().resolve(strict=False) if current_workspace_root is not None else None,
    ]
    for candidate in paper_live_path_candidates(
        text,
        source_root=source_root,
        current_workspace_root=current_workspace_root,
        legacy_workspace_roots=legacy_workspace_roots,
    ):
        if candidate.exists() or any(path_is_within(candidate, root) for root in candidate_roots if root is not None):
            return os.path.relpath(candidate, target_root).replace(os.sep, "/")
    return PurePosixPath(text).as_posix() if not Path(text).is_absolute() else text


def normalize_paper_live_path_list(
    values: object,
    *,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> list[str]:
    normalized: list[str] = []
    for raw in values or [] if isinstance(values, list) else []:
        text = normalize_paper_live_path(
            raw,
            source_root=source_root,
            target_root=target_root,
            current_workspace_root=current_workspace_root,
            legacy_workspace_roots=legacy_workspace_roots,
        )
        if text:
            normalized.append(text)
    return normalized


def normalize_selected_outline_live_payload(
    payload: dict[str, Any],
    *,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> dict[str, Any]:
    normalized = copy.deepcopy(payload if isinstance(payload, dict) else {})
    for section in normalized.get("sections") or [] if isinstance(normalized.get("sections"), list) else []:
        if not isinstance(section, dict):
            continue
        rows = section.get("result_table") if isinstance(section.get("result_table"), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            row["source_paths"] = normalize_paper_live_path_list(
                row.get("source_paths"),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
    return normalized


def normalize_paper_evidence_ledger_payload(
    payload: dict[str, Any],
    *,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> dict[str, Any]:
    normalized = copy.deepcopy(payload if isinstance(payload, dict) else {})
    items = normalized.get("items") if isinstance(normalized.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        item["source_paths"] = normalize_paper_live_path_list(
            item.get("source_paths"),
            source_root=source_root,
            target_root=target_root,
            current_workspace_root=current_workspace_root,
            legacy_workspace_roots=legacy_workspace_roots,
        )
    claims = normalized.get("claims") if isinstance(normalized.get("claims"), list) else []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        evidence_items = claim.get("evidence_items") if isinstance(claim.get("evidence_items"), list) else []
        for item in evidence_items:
            if not isinstance(item, dict):
                continue
            item["source_paths"] = normalize_paper_live_path_list(
                item.get("source_paths"),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
        evidence_entries = claim.get("evidence") if isinstance(claim.get("evidence"), list) else []
        for item in evidence_entries:
            if not isinstance(item, dict):
                continue
            item["source_paths"] = normalize_paper_live_path_list(
                item.get("source_paths"),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
    return normalized


def normalize_claim_evidence_map_payload(
    payload: dict[str, Any],
    *,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> dict[str, Any]:
    normalized = copy.deepcopy(payload if isinstance(payload, dict) else {})
    claims = normalized.get("claims") if isinstance(normalized.get("claims"), list) else []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        items = claim.get("evidence_items") if isinstance(claim.get("evidence_items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            item["source_paths"] = normalize_paper_live_path_list(
                item.get("source_paths"),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
    return normalized


def normalize_display_catalog_payload(
    payload: dict[str, Any],
    *,
    collection_key: str,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> dict[str, Any]:
    normalized = copy.deepcopy(payload if isinstance(payload, dict) else {})
    entries = normalized.get(collection_key) if isinstance(normalized.get(collection_key), list) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for field_name in ("source_paths", "asset_paths", "export_paths"):
            if field_name not in entry:
                continue
            entry[field_name] = normalize_paper_live_path_list(
                entry.get(field_name),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
        qc_result = entry.get("qc_result")
        if isinstance(qc_result, dict) and "layout_sidecar_path" in qc_result:
            qc_result["layout_sidecar_path"] = normalize_paper_live_path(
                qc_result.get("layout_sidecar_path"),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
    return normalized


def normalize_paper_baseline_inventory_payload(
    payload: dict[str, Any],
    *,
    source_root: Path,
    target_root: Path,
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> dict[str, Any]:
    normalized = copy.deepcopy(payload if isinstance(payload, dict) else {})

    def normalize_entry(entry: object) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None
        resolved = dict(entry)
        for key in (
            "baseline_path",
            "baseline_root_rel_path",
            "metric_contract_json_path",
            "metric_contract_json_rel_path",
        ):
            if key in resolved:
                resolved[key] = normalize_paper_live_path(
                    resolved.get(key),
                    source_root=source_root,
                    target_root=target_root,
                    current_workspace_root=current_workspace_root,
                    legacy_workspace_roots=legacy_workspace_roots,
                )
        if "evidence_paths" in resolved:
            resolved["evidence_paths"] = normalize_paper_live_path_list(
                resolved.get("evidence_paths"),
                source_root=source_root,
                target_root=target_root,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
        return resolved

    canonical = normalize_entry(normalized.get("canonical_baseline_ref"))
    normalized["canonical_baseline_ref"] = canonical
    entries = normalized.get("supplementary_baselines") if isinstance(normalized.get("supplementary_baselines"), list) else []
    normalized["supplementary_baselines"] = [
        item
        for item in (normalize_entry(entry) for entry in entries)
        if isinstance(item, dict)
    ]
    return normalized


def paper_bundle_surface_override(
    raw_path: object,
    *,
    source_root: Path,
    target_paper_root: Path,
    candidate_paper_roots: list[Path],
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> Path | None:
    text = str(raw_path or "").strip()
    if not text:
        return None
    candidate_roots = [target_paper_root, *candidate_paper_roots]
    seen_roots: set[str] = set()
    paper_roots: list[Path] = []
    for paper_root in candidate_roots:
        resolved_root = paper_root.resolve(strict=False)
        key = str(resolved_root)
        if key in seen_roots:
            continue
        seen_roots.add(key)
        paper_roots.append(resolved_root)
    for candidate in paper_live_path_candidates(
        text,
        source_root=source_root,
        current_workspace_root=current_workspace_root,
        legacy_workspace_roots=legacy_workspace_roots,
    ):
        for paper_root in paper_roots:
            try:
                relative = candidate.resolve(strict=False).relative_to(paper_root)
            except ValueError:
                continue
            return target_paper_root / relative
    return None


def normalize_paper_bundle_manifest_payload(
    payload: dict[str, Any],
    *,
    source_root: Path,
    target_paper_root: Path,
    candidate_paper_roots: list[Path],
    current_workspace_root: Path | None = None,
    legacy_workspace_roots: list[Path] | None = None,
) -> dict[str, Any]:
    target_root = target_paper_root.parent
    normalized = copy.deepcopy(payload if isinstance(payload, dict) else {})
    local_overrides = {
        "outline_path": target_paper_root / "selected_outline.json",
        "draft_path": target_paper_root / "draft.md",
        "writing_plan_path": target_paper_root / "writing_plan.md",
        "references_path": target_paper_root / "references.bib",
        "claim_evidence_map_path": target_paper_root / "claim_evidence_map.json",
        "evidence_ledger_path": target_paper_root / "evidence_ledger.json",
        "compile_report_path": target_paper_root / "build" / "compile_report.json",
        "pdf_path": target_paper_root / "paper.pdf",
        "baseline_inventory_path": target_paper_root / "baseline_inventory.json",
    }
    optional_local_overrides = {
        "experiment_matrix_path": target_paper_root / "paper_experiment_matrix.md",
        "experiment_matrix_json_path": target_paper_root / "paper_experiment_matrix.json",
    }
    for key, path in optional_local_overrides.items():
        if path.exists():
            local_overrides[key] = path
    for key in (
        "outline_path",
        "draft_path",
        "writing_plan_path",
        "references_path",
        "claim_evidence_map_path",
        "evidence_ledger_path",
        "experiment_matrix_path",
        "experiment_matrix_json_path",
        "compile_report_path",
        "pdf_path",
        "latex_root_path",
        "baseline_inventory_path",
        "open_source_manifest_path",
        "open_source_cleanup_plan_path",
    ):
        if key not in normalized:
            continue
        if key not in local_overrides:
            surface_override = paper_bundle_surface_override(
                normalized.get(key),
                source_root=source_root,
                target_paper_root=target_paper_root,
                candidate_paper_roots=candidate_paper_roots,
                current_workspace_root=current_workspace_root,
                legacy_workspace_roots=legacy_workspace_roots,
            )
            if surface_override is not None:
                local_overrides[key] = surface_override
        normalized[key] = normalize_paper_live_path(
            normalized.get(key),
            source_root=source_root,
            target_root=target_root,
            current_workspace_root=current_workspace_root,
            legacy_workspace_roots=legacy_workspace_roots,
            target_override=local_overrides.get(key),
        )
    evidence_gate = dict(normalized.get("evidence_gate") or {}) if isinstance(normalized.get("evidence_gate"), dict) else {}
    if "outline_path" in evidence_gate:
        evidence_gate["outline_path"] = normalize_paper_live_path(
            evidence_gate.get("outline_path"),
            source_root=source_root,
            target_root=target_root,
            current_workspace_root=current_workspace_root,
            legacy_workspace_roots=legacy_workspace_roots,
            target_override=target_paper_root / "selected_outline.json",
        )
    normalized["evidence_gate"] = evidence_gate
    return normalized


def paper_bundle_relative_path(path: Path | None, *, roots: list[Path]) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve())
        if key in seen:
            continue
        seen.add(key)
        try:
            return resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    return str(path)
