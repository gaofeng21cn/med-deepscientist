from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

RUNTIME_PROTOCOL_REF = "docs/policies/runtime_protocol.md"
TRANSITION_CONTRACT_REF = "docs/policies/mas_mds_transition_contract.md"

PROMOTION_LADDER_STAGES = (
    "retain_in_mds_backend",
    "oracle_only",
    "promote_to_runtime_protocol",
    "mas_owned_or_absorbed",
)

BOUNDARY_STATUS_BY_STAGE = {
    "retain_in_mds_backend": "retain_backend",
    "oracle_only": "oracle_only",
    "promote_to_runtime_protocol": "promote_runtime_protocol",
    "mas_owned_or_absorbed": "mas_owned_or_absorbed",
}

DEFAULT_AUDIT_FILE_SUFFIXES = (".py", ".md", ".toml", ".yaml", ".yml", ".sh")
DEFAULT_SKIP_DIR_NAMES = (
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
)

MAS_OWNER_AUTHORITIES = frozenset(
    {
        "medical_research_design",
        "medical_evidence_interpretation",
        "publication_readiness",
        "submission_authority",
        "user_visible_research_progress",
    }
)

_REQUIRED_SURFACE_FIELDS = (
    "surface",
    "current_owner",
    "target_owner",
    "strangler_stage",
    "mas_consumable_contract",
    "promotion_gate",
    "parity_proof",
    "rollback_surface",
)

_CONSUMPTION_REPORT_FIELDS = (
    "owner",
    "target_owner",
    "stage",
    "promotion_gate",
    "parity_proof",
    "rollback_surface",
    "mas_consumable_status",
)

_BASE_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "surface": "daemon_api_minimum",
        "current_owner": "MedDeepScientist controlled backend",
        "target_owner": "MedAutoScience runtime adapter",
        "strangler_stage": "promote_to_runtime_protocol",
        "mas_consumable_contract": True,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "runtime and API contract regression tests",
        "rollback_surface": "daemon API minimum stable protocol",
        "owner_authority": "runtime_protocol",
    },
    {
        "surface": "quest_runtime_layout",
        "current_owner": "MedDeepScientist controlled backend",
        "target_owner": "MedAutoScience runtime adapter",
        "strangler_stage": "promote_to_runtime_protocol",
        "mas_consumable_contract": True,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "runtime contract and quest layout regression tests",
        "rollback_surface": "quest durable layout stable protocol",
        "owner_authority": "runtime_protocol",
    },
    {
        "surface": "native_runtime_event_surface",
        "current_owner": "MedDeepScientist controlled backend",
        "target_owner": "MedAutoScience runtime adapter",
        "strangler_stage": "promote_to_runtime_protocol",
        "mas_consumable_contract": True,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "native runtime truth regression tests",
        "rollback_surface": "quest-local runtime_event durable artifact",
        "owner_authority": "runtime_protocol",
    },
    {
        "surface": "runner_dispatch_selection",
        "current_owner": "MedDeepScientist controlled backend",
        "target_owner": "MedAutoScience runtime adapter",
        "strangler_stage": "promote_to_runtime_protocol",
        "mas_consumable_contract": True,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "runner metadata and runtime override regression tests",
        "rollback_surface": "executor_kind and runner lane protocol",
        "owner_authority": "runtime_protocol",
    },
    {
        "surface": "prompt_prose_and_stage_skill_wording",
        "current_owner": "MedDeepScientist behavior oracle",
        "target_owner": "MedAutoScience parity oracle",
        "strangler_stage": "oracle_only",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "prompt builder and stage skill regression tests",
        "rollback_surface": "repo-local prompt and skill fixtures",
        "owner_authority": "behavior_oracle",
    },
    {
        "surface": "ui_tui_rendering_payload",
        "current_owner": "MedDeepScientist behavior oracle",
        "target_owner": "MedAutoScience parity oracle",
        "strangler_stage": "oracle_only",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "TUI and UI source contract regression tests",
        "rollback_surface": "UI/TUI rendering fixtures",
        "owner_authority": "behavior_oracle",
    },
    {
        "surface": "publication_readiness_authority",
        "current_owner": "MedAutoScience product owner",
        "target_owner": "MedAutoScience product owner",
        "strangler_stage": "mas_owned_or_absorbed",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "MAS publication gate and controller decision proof",
        "rollback_surface": "MDS oracle fixture only",
        "owner_authority": "publication_readiness",
    },
    {
        "surface": "medical_research_design_authority",
        "current_owner": "MedAutoScience product owner",
        "target_owner": "MedAutoScience product owner",
        "strangler_stage": "mas_owned_or_absorbed",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "MAS study intake and medical controller proof",
        "rollback_surface": "MDS oracle fixture only",
        "owner_authority": "medical_research_design",
    },
    {
        "surface": "medical_evidence_interpretation_authority",
        "current_owner": "MedAutoScience product owner",
        "target_owner": "MedAutoScience product owner",
        "strangler_stage": "mas_owned_or_absorbed",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "MAS evidence ledger and publication evaluation proof",
        "rollback_surface": "MDS oracle fixture only",
        "owner_authority": "medical_evidence_interpretation",
    },
    {
        "surface": "submission_package_authority",
        "current_owner": "MedAutoScience product owner",
        "target_owner": "MedAutoScience product owner",
        "strangler_stage": "mas_owned_or_absorbed",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "MAS submission package gate proof",
        "rollback_surface": "MDS oracle fixture only",
        "owner_authority": "submission_authority",
    },
    {
        "surface": "user_visible_study_progress",
        "current_owner": "MedAutoScience product owner",
        "target_owner": "MedAutoScience product owner",
        "strangler_stage": "mas_owned_or_absorbed",
        "mas_consumable_contract": False,
        "promotion_gate": TRANSITION_CONTRACT_REF,
        "parity_proof": "MAS study runtime status and controller progress proof",
        "rollback_surface": "MDS runtime status oracle fixture only",
        "owner_authority": "user_visible_research_progress",
    },
)


def validate_promotion_ladder_stage(
    strangler_stage: str,
    *,
    runtime_protocol_ref: str | None = None,
) -> str:
    normalized_stage = str(strangler_stage or "").strip()
    if normalized_stage not in PROMOTION_LADDER_STAGES:
        allowed = ", ".join(PROMOTION_LADDER_STAGES)
        raise ValueError(f"Unknown MAS/MDS promotion ladder stage `{normalized_stage}`. Expected one of: {allowed}.")
    if (
        normalized_stage == "promote_to_runtime_protocol"
        and str(runtime_protocol_ref or "").strip() != RUNTIME_PROTOCOL_REF
    ):
        raise ValueError(f"`promote_to_runtime_protocol` requires runtime protocol reference `{RUNTIME_PROTOCOL_REF}`.")
    return normalized_stage


def normalize_surface_record(record: Mapping[str, Any]) -> dict[str, Any]:
    missing_fields = [field for field in _REQUIRED_SURFACE_FIELDS if field not in record]
    if missing_fields:
        raise ValueError(f"Strangler surface record is missing required fields: {', '.join(missing_fields)}.")

    normalized = dict(record)
    for field in _REQUIRED_SURFACE_FIELDS:
        if field == "mas_consumable_contract":
            normalized[field] = bool(record[field])
            continue
        normalized[field] = str(record[field] or "").strip()
        if not normalized[field]:
            raise ValueError(f"Strangler surface record field `{field}` must be non-empty.")

    normalized["strangler_stage"] = validate_promotion_ladder_stage(
        str(normalized["strangler_stage"]),
        runtime_protocol_ref=str(normalized["promotion_gate"]),
    )
    if normalized["mas_consumable_contract"] and normalized["strangler_stage"] != "promote_to_runtime_protocol":
        raise ValueError("MAS-consumable MDS surfaces must be promoted through the runtime protocol.")
    if normalized["strangler_stage"] == "promote_to_runtime_protocol" and not normalized["mas_consumable_contract"]:
        raise ValueError("Runtime protocol promoted surfaces must be marked as MAS-consumable contracts.")

    owner_authority = str(record.get("owner_authority") or "").strip()
    if owner_authority:
        normalized["owner_authority"] = owner_authority
    owner_authorities = _owner_authorities(record)
    if owner_authorities:
        normalized["owner_authorities"] = list(owner_authorities)
        if len(owner_authorities) == 1:
            normalized["owner_authority"] = owner_authorities[0]
    notes = record.get("notes")
    if isinstance(notes, Sequence) and not isinstance(notes, str):
        normalized["notes"] = [str(item).strip() for item in notes if str(item).strip()]
    return normalized


def mas_consumption_contract_report(
    surfaces: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    surface_records = _surface_records_for_report(surfaces)
    report_surfaces: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for record in surface_records:
        entry, entry_issues = _mas_consumption_contract_entry(record)
        report_surfaces.append(entry)
        issues.extend(entry_issues)
    return {
        "schema_version": 1,
        "ok": not issues,
        "surface_count": len(report_surfaces),
        "surfaces": report_surfaces,
        "issue_count": len(issues),
        "issues": issues,
    }


def mas_consumption_contract_issues(surfaces: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return mas_consumption_contract_report(surfaces)["issues"]


def surface_boundary_read_model(
    surfaces: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    contract_report = mas_consumption_contract_report(surfaces)
    read_model_surfaces: list[dict[str, Any]] = []
    for surface in contract_report["surfaces"]:
        entry = dict(surface)
        entry["boundary_status"] = BOUNDARY_STATUS_BY_STAGE.get(str(entry.get("stage") or ""), "invalid")
        read_model_surfaces.append(entry)
    return {
        "schema_version": 1,
        "ok": contract_report["ok"],
        "boundary_statuses": [surface["boundary_status"] for surface in read_model_surfaces],
        "surface_count": len(read_model_surfaces),
        "surfaces": read_model_surfaces,
        "issue_count": contract_report["issue_count"],
        "issues": contract_report["issues"],
        "mas_consumption_contract_report": contract_report,
    }


def default_strangler_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for record in _BASE_SURFACES:
        normalized = normalize_surface_record(record)
        registry[normalized["surface"]] = normalized

    from .artifact.service_parts import artifact_inventory

    for surface in ("analysis_baseline_inventory", "paper_baseline_inventory"):
        record = artifact_inventory.artifact_inventory_surface_audit(surface)
        record.setdefault("owner_authority", "behavior_oracle")
        normalized = normalize_surface_record(record)
        registry[normalized["surface"]] = normalized
    return registry


def owner_reflux_issues(surfaces: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for raw_record in surfaces:
        try:
            record = normalize_surface_record(raw_record)
        except ValueError as exc:
            surface = str(raw_record.get("surface") or "<unknown>") if isinstance(raw_record, Mapping) else "<unknown>"
            issues.append(
                {
                    "code": "surface_registry_error",
                    "surface": surface,
                    "message": str(exc),
                }
            )
            continue
        owner_authorities = [authority for authority in _owner_authorities(record) if authority in MAS_OWNER_AUTHORITIES]
        if owner_authorities and record["strangler_stage"] != "mas_owned_or_absorbed":
            issue = {
                "code": "owner_reflux_risk",
                "surface": record["surface"],
                "owner_authorities": owner_authorities,
                "strangler_stage": record["strangler_stage"],
                "current_owner": record["current_owner"],
                "target_owner": record["target_owner"],
                "message": "MAS owner authority must stay on the `mas_owned_or_absorbed` side of the boundary.",
            }
            if len(owner_authorities) == 1:
                issue["owner_authority"] = owner_authorities[0]
            issues.append(
                issue
            )
    return issues


def _surface_records_for_report(
    surfaces: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None,
) -> list[Mapping[str, Any]]:
    if surfaces is None:
        return list(default_strangler_registry().values())
    if isinstance(surfaces, Mapping):
        if "surface" in surfaces:
            return [dict(surfaces)]
        return [dict(record) for record in surfaces.values()]
    return list(surfaces)


def _mas_consumption_contract_entry(record: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = dict(record)
    entry = {
        "surface": _text(raw.get("surface")) or "<unknown>",
        "owner": _text(raw.get("current_owner")),
        "current_owner": _text(raw.get("current_owner")),
        "target_owner": _text(raw.get("target_owner")),
        "stage": _text(raw.get("strangler_stage")),
        "strangler_stage": _text(raw.get("strangler_stage")),
        "promotion_gate": _text(raw.get("promotion_gate")),
        "parity_proof": _text(raw.get("parity_proof")),
        "rollback_surface": _text(raw.get("rollback_surface")),
        "mas_consumable": bool(raw.get("mas_consumable_contract")),
        "mas_consumable_contract": bool(raw.get("mas_consumable_contract")),
    }
    owner_authority = _text(raw.get("owner_authority"))
    if owner_authority:
        entry["owner_authority"] = owner_authority
    owner_authorities = _owner_authorities(raw)
    if owner_authorities:
        entry["owner_authorities"] = list(owner_authorities)
        if len(owner_authorities) == 1:
            entry["owner_authority"] = owner_authorities[0]

    issues = _mas_consumption_contract_entry_issues(entry, raw)
    if not issues:
        try:
            normalized = normalize_surface_record(raw)
        except ValueError as exc:
            issues.append(
                {
                    "code": "surface_registry_error",
                    "surface": entry["surface"],
                    "message": str(exc),
                }
            )
        else:
            entry.update(
                {
                    "surface": normalized["surface"],
                    "owner": normalized["current_owner"],
                    "current_owner": normalized["current_owner"],
                    "target_owner": normalized["target_owner"],
                    "stage": normalized["strangler_stage"],
                    "strangler_stage": normalized["strangler_stage"],
                    "promotion_gate": normalized["promotion_gate"],
                    "parity_proof": normalized["parity_proof"],
                    "rollback_surface": normalized["rollback_surface"],
                    "mas_consumable": normalized["mas_consumable_contract"],
                    "mas_consumable_contract": normalized["mas_consumable_contract"],
                }
            )
            if "owner_authority" in normalized:
                entry["owner_authority"] = normalized["owner_authority"]
            if "owner_authorities" in normalized:
                entry["owner_authorities"] = list(normalized["owner_authorities"])
    entry["mas_consumable_status"] = _mas_consumable_status(entry, issues)
    entry["report_fields"] = list(_CONSUMPTION_REPORT_FIELDS)
    if issues:
        entry["issues"] = [dict(issue) for issue in issues]
    return entry, issues


def _mas_consumption_contract_entry_issues(
    entry: Mapping[str, Any],
    raw: Mapping[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    surface = str(entry["surface"])
    missing_fields = [field for field in _REQUIRED_SURFACE_FIELDS if field not in raw]
    if missing_fields:
        issues.append(
            {
                "code": "surface_registry_error",
                "surface": surface,
                "missing_fields": missing_fields,
                "message": f"Strangler surface record is missing required fields: {', '.join(missing_fields)}.",
            }
        )

    stage = str(entry["stage"])
    if stage and stage not in PROMOTION_LADDER_STAGES:
        allowed = ", ".join(PROMOTION_LADDER_STAGES)
        issues.append(
            {
                "code": "surface_registry_error",
                "surface": surface,
                "strangler_stage": stage,
                "message": f"Unknown MAS/MDS promotion ladder stage `{stage}`. Expected one of: {allowed}.",
            }
        )

    mas_consumable = bool(entry["mas_consumable_contract"])
    if mas_consumable:
        if stage != "promote_to_runtime_protocol":
            issues.append(
                {
                    "code": "mas_consumable_invalid_stage",
                    "surface": surface,
                    "strangler_stage": stage,
                    "message": "MAS-consumable MDS surfaces must be promoted through the runtime protocol.",
                }
            )
        if entry["promotion_gate"] != RUNTIME_PROTOCOL_REF:
            issues.append(
                {
                    "code": "mas_consumable_missing_runtime_protocol_gate",
                    "surface": surface,
                    "promotion_gate": entry["promotion_gate"],
                    "required_promotion_gate": RUNTIME_PROTOCOL_REF,
                    "message": "MAS-consumable MDS surfaces must use the runtime protocol promotion gate.",
                }
            )
        if not entry["parity_proof"]:
            issues.append(
                {
                    "code": "mas_consumable_missing_parity_proof",
                    "surface": surface,
                    "message": "MAS-consumable MDS surfaces must declare a parity proof.",
                }
            )

    owner_authorities = [authority for authority in _owner_authorities(entry) if authority in MAS_OWNER_AUTHORITIES]
    if owner_authorities and stage != "mas_owned_or_absorbed":
        issue = {
            "code": "owner_reflux_risk",
            "surface": surface,
            "owner_authorities": owner_authorities,
            "strangler_stage": stage,
            "current_owner": entry["current_owner"],
            "target_owner": entry["target_owner"],
            "message": "MAS owner authority must stay on the `mas_owned_or_absorbed` side of the boundary.",
        }
        if len(owner_authorities) == 1:
            issue["owner_authority"] = owner_authorities[0]
        issues.append(issue)
    return issues


def _mas_consumable_status(entry: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> str:
    issue_codes = {str(issue.get("code") or "") for issue in issues}
    if "owner_reflux_risk" in issue_codes:
        return "blocked_owner_reflux"
    if "mas_consumable_missing_runtime_protocol_gate" in issue_codes:
        return "blocked_missing_runtime_protocol_gate"
    if "mas_consumable_missing_parity_proof" in issue_codes:
        return "blocked_missing_parity_proof"
    if issue_codes:
        return "blocked_invalid_surface"
    if bool(entry["mas_consumable_contract"]):
        return "mas_consumable"
    if entry["stage"] == "mas_owned_or_absorbed":
        return "mas_owned_or_absorbed"
    return "not_mas_consumable"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _owner_authorities(record: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    raw_authorities = record.get("owner_authorities")
    if isinstance(raw_authorities, Sequence) and not isinstance(raw_authorities, str):
        values.extend(str(item).strip() for item in raw_authorities)
    elif raw_authorities:
        values.append(str(raw_authorities).strip())

    owner_authority = str(record.get("owner_authority") or "").strip()
    if owner_authority:
        values.append(owner_authority)

    return tuple(dict.fromkeys(value for value in values if value))


def oversized_file_issues(
    root: Path,
    *,
    max_file_lines: int = 1500,
    include_file_suffixes: Sequence[str] = DEFAULT_AUDIT_FILE_SUFFIXES,
    skip_dir_names: Sequence[str] = DEFAULT_SKIP_DIR_NAMES,
) -> list[dict[str, Any]]:
    root_path = Path(root)
    suffixes = tuple(str(suffix) for suffix in include_file_suffixes)
    skip_names = set(skip_dir_names)
    issues: list[dict[str, Any]] = []
    for current_dir, dir_names, file_names in os.walk(root_path):
        dir_names[:] = [name for name in dir_names if name not in skip_names]
        current_path = Path(current_dir)
        for file_name in file_names:
            file_path = current_path / file_name
            if suffixes and file_path.suffix not in suffixes:
                continue
            line_count = _count_file_lines(file_path)
            if line_count <= max_file_lines:
                continue
            issues.append(
                {
                    "code": "oversized_file",
                    "path": file_path.relative_to(root_path).as_posix(),
                    "line_count": line_count,
                    "max_file_lines": max_file_lines,
                    "message": "File exceeds the MAS/MDS boundary guard line budget.",
                }
            )
    return issues


def boundary_guard_report(
    root: Path,
    *,
    surfaces: Iterable[Mapping[str, Any]] | None = None,
    max_file_lines: int = 1500,
    include_file_suffixes: Sequence[str] = DEFAULT_AUDIT_FILE_SUFFIXES,
    skip_dir_names: Sequence[str] = DEFAULT_SKIP_DIR_NAMES,
) -> dict[str, Any]:
    root_path = Path(root)
    surface_records = list(surfaces) if surfaces is not None else list(default_strangler_registry().values())
    contract_report = mas_consumption_contract_report(surface_records)
    issues = [
        *contract_report["issues"],
        *oversized_file_issues(
            root_path,
            max_file_lines=max_file_lines,
            include_file_suffixes=include_file_suffixes,
            skip_dir_names=skip_dir_names,
        ),
    ]
    return {
        "schema_version": 1,
        "ok": not issues,
        "root": str(root_path),
        "mas_consumption_contract_report": contract_report,
        "issue_count": len(issues),
        "issues": issues,
    }


def _count_file_lines(file_path: Path) -> int:
    with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _line in handle)
