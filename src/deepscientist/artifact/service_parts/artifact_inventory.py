from __future__ import annotations

from pathlib import Path
from typing import Any

from ...shared import ensure_dir, read_json, utc_now, write_json
from ...strangler_registry import (
    PROMOTION_LADDER_STAGES,
    RUNTIME_PROTOCOL_REF,
    mas_consumption_contract_report,
    validate_promotion_ladder_stage,
)

_SURFACE_AUDITS: dict[str, dict[str, Any]] = {
    "analysis_baseline_inventory": {
        "surface": "analysis_baseline_inventory",
        "current_owner": "MedDeepScientist",
        "target_owner": "MedAutoScience parity oracle",
        "strangler_stage": "oracle_only",
        "mas_consumable_contract": False,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "targeted artifact inventory regression tests",
        "rollback_surface": "quest-local artifacts/baselines/analysis_inventory.json",
        "owner_authority": "behavior_oracle",
    },
    "paper_baseline_inventory": {
        "surface": "paper_baseline_inventory",
        "current_owner": "MedDeepScientist",
        "target_owner": "MedAutoScience parity oracle",
        "strangler_stage": "oracle_only",
        "mas_consumable_contract": False,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "targeted artifact inventory regression tests",
        "rollback_surface": "quest-local paper/baseline_inventory.json",
        "owner_authority": "behavior_oracle",
    },
}


def artifact_inventory_surface_audit(surface: str) -> dict[str, Any]:
    normalized_surface = str(surface or "").strip()
    audit = _SURFACE_AUDITS.get(normalized_surface)
    if audit is None:
        known = ", ".join(sorted(_SURFACE_AUDITS))
        raise ValueError(f"Unknown artifact inventory surface `{normalized_surface}`. Expected one of: {known}.")
    validate_promotion_ladder_stage(str(audit["strangler_stage"]))
    return dict(audit)


def artifact_inventory_surface_contract_report() -> dict[str, Any]:
    return mas_consumption_contract_report(_SURFACE_AUDITS.values())


def analysis_baseline_inventory_path(quest_root: Path) -> Path:
    return ensure_dir(quest_root / "artifacts" / "baselines") / "analysis_inventory.json"


def read_analysis_baseline_inventory(quest_root: Path) -> dict[str, Any]:
    payload = read_json(analysis_baseline_inventory_path(quest_root), {})
    if not isinstance(payload, dict):
        payload = {}
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    return {
        "schema_version": 1,
        "entries": [dict(item) for item in entries if isinstance(item, dict)],
        "updated_at": payload.get("updated_at"),
    }


def write_analysis_baseline_inventory(quest_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    normalized_entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    normalized = {
        "schema_version": 1,
        "entries": [dict(item) for item in normalized_entries if isinstance(item, dict)],
        "updated_at": utc_now(),
    }
    write_json(analysis_baseline_inventory_path(quest_root), normalized)
    return normalized


def analysis_inventory_entry_key(payload: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    origin = dict(payload.get("origin") or {}) if isinstance(payload.get("origin"), dict) else {}
    return (
        str(payload.get("baseline_id") or "").strip(),
        str(payload.get("variant_id") or "").strip(),
        str(origin.get("campaign_id") or "").strip(),
        str(origin.get("slice_id") or "").strip(),
        str(payload.get("benchmark") or "").strip(),
        str(payload.get("split") or "").strip(),
    )


def merge_analysis_inventory_entry(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        merged[key] = value
    merged["updated_at"] = utc_now()
    merged.setdefault("created_at", existing.get("created_at") or incoming.get("created_at") or utc_now())
    return merged


def upsert_analysis_baseline_inventory(quest_root: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    inventory = read_analysis_baseline_inventory(quest_root)
    existing_entries = [dict(item) for item in (inventory.get("entries") or []) if isinstance(item, dict)]
    by_key = {
        analysis_inventory_entry_key(item): dict(item)
        for item in existing_entries
        if str(item.get("baseline_id") or "").strip()
    }
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        entry = dict(raw)
        if not str(entry.get("baseline_id") or "").strip():
            continue
        key = analysis_inventory_entry_key(entry)
        current = by_key.get(key)
        if current is None:
            stamped = dict(entry)
            stamped.setdefault("created_at", utc_now())
            stamped["updated_at"] = utc_now()
            by_key[key] = stamped
            continue
        by_key[key] = merge_analysis_inventory_entry(current, entry)
    return write_analysis_baseline_inventory(quest_root, {"entries": list(by_key.values())})


def build_paper_baseline_inventory_payload(
    *,
    quest_yaml: dict[str, Any],
    analysis_inventory: dict[str, Any],
) -> dict[str, Any]:
    confirmed_baseline_ref = (
        dict(quest_yaml.get("confirmed_baseline_ref") or {})
        if isinstance(quest_yaml.get("confirmed_baseline_ref"), dict)
        else None
    )
    return {
        "schema_version": 1,
        "canonical_baseline_ref": confirmed_baseline_ref,
        "supplementary_baselines": [
            dict(item) for item in (analysis_inventory.get("entries") or []) if isinstance(item, dict)
        ],
        "surface_audit": artifact_inventory_surface_audit("paper_baseline_inventory"),
        "updated_at": utc_now(),
    }
