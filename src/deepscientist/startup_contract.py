from __future__ import annotations

from copy import deepcopy
from typing import Any

RUNTIME_OWNED_STARTUP_CONTRACT_KEYS: tuple[str, ...] = (
    "schema_version",
    "user_language",
    "need_research_paper",
    "publishability_gate_mode",
    "decision_policy",
    "launch_mode",
    "standard_profile",
    "custom_profile",
    "baseline_execution_policy",
    "review_followup_policy",
    "manuscript_edit_mode",
)

CONTROLLER_OWNED_STARTUP_CONTRACT_EXTENSION_KEYS: tuple[str, ...] = (
    "research_intensity",
    "scope",
    "baseline_mode",
    "resource_policy",
    "time_budget_hours",
    "git_strategy",
    "runtime_constraints",
    "objectives",
    "baseline_urls",
    "paper_urls",
    "entry_state_summary",
    "review_summary",
    "controller_first_policy_summary",
    "automation_ready_summary",
    "custom_brief",
    "required_first_anchor",
    "legacy_code_execution_allowed",
    "startup_boundary_gate",
    "runtime_reentry_gate",
    "journal_shortlist",
    "medical_analysis_contract_summary",
    "medical_reporting_contract_summary",
    "reporting_guideline_family",
    "submission_targets",
)

_OPTIONAL_STRING_RUNTIME_KEYS = {
    "user_language",
    "decision_policy",
    "launch_mode",
    "standard_profile",
    "custom_profile",
    "baseline_execution_policy",
    "review_followup_policy",
    "manuscript_edit_mode",
}

_PUBLISHABILITY_GATE_MODES = {"off", "warn", "enforce"}


def _normalize_runtime_owned_value(*, key: str, value: object) -> Any:
    if key == "schema_version":
        if not isinstance(value, int):
            raise TypeError("startup_contract.schema_version must be an integer")
        return value
    if key == "need_research_paper":
        if not isinstance(value, bool):
            raise TypeError("startup_contract.need_research_paper must be a boolean")
        return value
    if key == "publishability_gate_mode":
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise TypeError("startup_contract.publishability_gate_mode must be one of off, warn, enforce, or null")
        normalized = value.strip().lower()
        if normalized not in _PUBLISHABILITY_GATE_MODES:
            raise TypeError("startup_contract.publishability_gate_mode must be one of off, warn, enforce, or null")
        return normalized
    if key in _OPTIONAL_STRING_RUNTIME_KEYS:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise TypeError(f"startup_contract.{key} must be a non-empty string or null")
        return value.strip()
    return deepcopy(value)


def normalize_startup_contract(
    startup_contract: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if startup_contract is None:
        return None
    if not isinstance(startup_contract, dict):
        raise TypeError("startup_contract must be a dict or null")
    normalized: dict[str, Any] = {}
    for key in RUNTIME_OWNED_STARTUP_CONTRACT_KEYS:
        if key in startup_contract:
            normalized[key] = _normalize_runtime_owned_value(key=key, value=startup_contract[key])
    for key, value in startup_contract.items():
        if key in normalized:
            continue
        normalized[key] = deepcopy(value)
    return normalized


def runtime_owned_startup_contract(
    startup_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalize_startup_contract(startup_contract) or {}
    return {key: normalized[key] for key in RUNTIME_OWNED_STARTUP_CONTRACT_KEYS if key in normalized}


def startup_contract_need_research_paper(
    startup_contract: dict[str, Any] | None,
    *,
    default: bool = True,
) -> bool:
    if not isinstance(startup_contract, dict):
        return default
    value = startup_contract.get("need_research_paper")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return default


def startup_contract_extensions(
    startup_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalize_startup_contract(startup_contract) or {}
    return {
        key: value
        for key, value in normalized.items()
        if key not in RUNTIME_OWNED_STARTUP_CONTRACT_KEYS
    }
