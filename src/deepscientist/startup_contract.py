from __future__ import annotations

from copy import deepcopy
from typing import Any

RUNTIME_OWNED_STARTUP_CONTRACT_KEYS: tuple[str, ...] = (
    "schema_version",
    "user_language",
    "need_research_paper",
    "publishability_gate_mode",
    "decision_policy",
    "control_mode",
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
    "control_mode",
    "launch_mode",
    "standard_profile",
    "custom_profile",
    "baseline_execution_policy",
    "review_followup_policy",
    "manuscript_edit_mode",
}

_PUBLISHABILITY_GATE_MODES = {"off", "warn", "enforce"}
_CONTROL_MODES = {"autonomous", "copilot"}

CONTROL_MODE_COPILOT_CONTINUATION_REASON = "control_mode_copilot"
CONTROL_MODE_AUTONOMOUS_CONTINUATION_REASON = "control_mode_autonomous"


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
    if key == "control_mode":
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise TypeError("startup_contract.control_mode must be one of autonomous, copilot, or null")
        normalized = value.strip().lower()
        if normalized not in _CONTROL_MODES:
            raise TypeError("startup_contract.control_mode must be one of autonomous, copilot, or null")
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


def startup_contract_control_mode(
    startup_contract: dict[str, Any] | None,
    *,
    default: str = "autonomous",
) -> str:
    if not isinstance(startup_contract, dict):
        return default
    value = str(startup_contract.get("control_mode") or "").strip().lower()
    if value in _CONTROL_MODES:
        return value
    return default


def reconcile_continuation_policy_for_control_mode(
    *,
    startup_contract: dict[str, Any] | None,
    continuation_policy: object,
    continuation_reason: object = None,
) -> dict[str, str] | None:
    control_mode = startup_contract_control_mode(startup_contract)
    normalized_policy = str(continuation_policy or "").strip().lower() or "auto"
    normalized_reason = str(continuation_reason or "").strip().lower() or None
    if control_mode == "copilot" and normalized_policy == "auto":
        return {
            "continuation_policy": "wait_for_user_or_resume",
            "continuation_reason": CONTROL_MODE_COPILOT_CONTINUATION_REASON,
        }
    if (
        control_mode == "autonomous"
        and normalized_policy == "wait_for_user_or_resume"
        and normalized_reason == CONTROL_MODE_COPILOT_CONTINUATION_REASON
    ):
        return {
            "continuation_policy": "auto",
            "continuation_reason": CONTROL_MODE_AUTONOMOUS_CONTINUATION_REASON,
        }
    return None
