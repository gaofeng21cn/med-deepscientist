from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from deepscientist.config import ConfigManager
from deepscientist.daemon.app import DaemonApp
from deepscientist.home import ensure_home_layout


def test_normalize_startup_contract_preserves_runtime_owned_subset_and_extensions() -> None:
    module = importlib.import_module("deepscientist.startup_contract")
    payload = {
        "schema_version": 4,
        "user_language": " zh ",
        "need_research_paper": True,
        "publishability_gate_mode": " warn ",
        "decision_policy": "autonomous",
        "launch_mode": "custom",
        "custom_profile": "continue_existing_state",
        "baseline_execution_policy": "reuse_existing_only",
        "review_followup_policy": None,
        "manuscript_edit_mode": "latex_required",
        "scope": "full_research",
        "entry_state_summary": "Study root: /tmp/studies/001-risk",
        "startup_boundary_gate": {"allow_compute_stage": False},
        "custom_brief": "keep passthrough",
    }

    normalized = module.normalize_startup_contract(payload)

    assert normalized == {
        "schema_version": 4,
        "user_language": "zh",
        "need_research_paper": True,
        "publishability_gate_mode": "warn",
        "decision_policy": "autonomous",
        "launch_mode": "custom",
        "custom_profile": "continue_existing_state",
        "baseline_execution_policy": "reuse_existing_only",
        "review_followup_policy": None,
        "manuscript_edit_mode": "latex_required",
        "scope": "full_research",
        "entry_state_summary": "Study root: /tmp/studies/001-risk",
        "startup_boundary_gate": {"allow_compute_stage": False},
        "custom_brief": "keep passthrough",
    }
    assert module.runtime_owned_startup_contract(payload) == {
        "schema_version": 4,
        "user_language": "zh",
        "need_research_paper": True,
        "publishability_gate_mode": "warn",
        "decision_policy": "autonomous",
        "launch_mode": "custom",
        "custom_profile": "continue_existing_state",
        "baseline_execution_policy": "reuse_existing_only",
        "review_followup_policy": None,
        "manuscript_edit_mode": "latex_required",
    }
    assert module.startup_contract_extensions(payload) == {
        "scope": "full_research",
        "entry_state_summary": "Study root: /tmp/studies/001-risk",
        "startup_boundary_gate": {"allow_compute_stage": False},
        "custom_brief": "keep passthrough",
    }


def test_quest_create_persists_normalized_runtime_owned_subset_and_extensions(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)

    payload = app.handlers.quest_create(
        {
            "goal": "Create quest with owned and extension startup contract.",
            "quest_id": "quest-startup-ownership",
            "startup_contract": {
                "schema_version": 4,
                "user_language": " zh ",
                "need_research_paper": False,
                "publishability_gate_mode": "enforce",
                "decision_policy": "autonomous",
                "launch_mode": "custom",
                "custom_profile": "continue_existing_state",
                "scope": "full_research",
                "entry_state_summary": "Study root: /tmp/studies/001-risk",
                "startup_boundary_gate": {"allow_compute_stage": False},
            },
        }
    )

    startup_contract = payload["snapshot"]["startup_contract"]
    assert startup_contract["schema_version"] == 4
    assert startup_contract["user_language"] == "zh"
    assert startup_contract["need_research_paper"] is False
    assert startup_contract["publishability_gate_mode"] == "enforce"
    assert startup_contract["decision_policy"] == "autonomous"
    assert startup_contract["launch_mode"] == "custom"
    assert startup_contract["custom_profile"] == "continue_existing_state"
    assert startup_contract["scope"] == "full_research"
    assert startup_contract["entry_state_summary"] == "Study root: /tmp/studies/001-risk"
    assert startup_contract["startup_boundary_gate"] == {"allow_compute_stage": False}


def test_quest_startup_context_patch_roundtrips_controller_owned_extensions(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create(
        "Patch startup contract ownership.",
        quest_id="quest-startup-extension-roundtrip",
        startup_contract={"launch_mode": "custom"},
    )

    payload = app.handlers.quest_startup_context(
        quest["quest_id"],
        {
            "startup_contract": {
                "launch_mode": "custom",
                "publishability_gate_mode": "off",
                "custom_profile": "continue_existing_state",
                "review_summary": "Need one stronger baseline comparison.",
                "submission_targets": [{"journal_name": "BMC Medicine"}],
            }
        },
    )

    startup_contract = payload["snapshot"]["startup_contract"]
    assert startup_contract["launch_mode"] == "custom"
    assert startup_contract["publishability_gate_mode"] == "off"
    assert startup_contract["custom_profile"] == "continue_existing_state"
    assert startup_contract["review_summary"] == "Need one stronger baseline comparison."
    assert startup_contract["submission_targets"] == [{"journal_name": "BMC Medicine"}]


def test_normalize_startup_contract_rejects_invalid_runtime_owned_type() -> None:
    module = importlib.import_module("deepscientist.startup_contract")

    with pytest.raises(TypeError, match="startup_contract.need_research_paper"):
        module.normalize_startup_contract({"need_research_paper": "yes"})


def test_normalize_startup_contract_rejects_invalid_publishability_gate_mode() -> None:
    module = importlib.import_module("deepscientist.startup_contract")

    with pytest.raises(TypeError, match="startup_contract.publishability_gate_mode"):
        module.normalize_startup_contract({"publishability_gate_mode": "maybe"})


def test_quest_create_rejects_invalid_runtime_owned_startup_contract_type(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)

    payload = app.handlers.quest_create(
        {
            "goal": "Reject invalid startup contract type.",
            "quest_id": "quest-invalid-startup-contract",
            "startup_contract": {
                "need_research_paper": "yes",
            },
        }
    )

    assert isinstance(payload, tuple)
    status_code, body = payload
    assert status_code == 400
    assert body["ok"] is False


def test_quest_startup_context_rejects_invalid_runtime_owned_startup_contract_type(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("Reject invalid startup contract patch.")

    payload = app.handlers.quest_startup_context(
        quest["quest_id"],
        {
            "startup_contract": {
                "schema_version": "4",
            }
        },
    )

    assert isinstance(payload, tuple)
    status_code, body = payload
    assert status_code == 400
    assert body["ok"] is False
