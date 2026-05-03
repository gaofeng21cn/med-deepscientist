from __future__ import annotations

import importlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_quest_runtime_audit_contract_normalizes_minimum_surface() -> None:
    module = importlib.import_module("deepscientist.daemon.runtime_contract")

    payload = module.build_quest_runtime_audit_contract(
        active_run_id="run-001",
        worker_running=True,
        worker_pending=False,
        stop_requested=False,
    )

    assert payload == {
        "ok": True,
        "status": "live",
        "source": "daemon_turn_worker",
        "active_run_id": "run-001",
        "worker_running": True,
        "worker_pending": False,
        "stop_requested": False,
    }


def test_quest_runtime_audit_contract_rejects_worker_without_active_run_id() -> None:
    module = importlib.import_module("deepscientist.daemon.runtime_contract")

    payload = module.build_quest_runtime_audit_contract(
        active_run_id=None,
        worker_running=True,
        worker_pending=False,
        stop_requested=False,
    )

    assert payload["status"] == "invalid"
    assert payload["active_run_id"] is None
    assert payload["worker_running"] is True


def test_quest_control_contract_requires_minimum_keys() -> None:
    module = importlib.import_module("deepscientist.daemon.runtime_contract")

    payload = module.build_quest_control_contract(
        {
            "ok": True,
            "quest_id": "quest-001",
            "action": "pause",
            "snapshot": {"status": "paused"},
        }
    )

    assert payload["ok"] is True
    assert payload["quest_id"] == "quest-001"
    assert payload["action"] == "pause"
    assert payload["status"] == "paused"
    assert payload["snapshot"] == {"status": "paused"}


def test_quest_startup_context_contract_requires_snapshot_quest_id() -> None:
    module = importlib.import_module("deepscientist.daemon.runtime_contract")

    payload = module.build_quest_startup_context_contract(
        {
            "quest_id": "quest-001",
            "startup_contract": {"scope": "full_research"},
        }
    )

    assert payload == {
        "ok": True,
        "quest_id": "quest-001",
        "snapshot": {
            "quest_id": "quest-001",
            "startup_contract": {"scope": "full_research"},
        },
    }


def test_quest_session_contract_requires_matching_quest_identity() -> None:
    module = importlib.import_module("deepscientist.daemon.runtime_contract")

    payload = module.build_quest_session_contract(
        quest_id="quest-001",
        snapshot={"quest_id": "quest-001", "status": "active"},
        runtime_audit={"ok": True, "status": "none"},
        acp_session={"id": "session-001"},
    )

    assert payload == {
        "ok": True,
        "quest_id": "quest-001",
        "snapshot": {"quest_id": "quest-001", "status": "active"},
        "runtime_audit": {"ok": True, "status": "none"},
        "acp_session": {"id": "session-001"},
    }


def test_artifact_completion_contract_preserves_minimum_surface() -> None:
    module = importlib.import_module("deepscientist.daemon.runtime_contract")

    payload = module.build_artifact_completion_contract(
        {
            "ok": True,
            "status": "completed",
            "snapshot": {"quest_id": "quest-001", "status": "completed"},
            "summary_refresh": {"ok": True},
        }
    )

    assert payload["ok"] is True
    assert payload["status"] == "completed"
    assert payload["snapshot"]["status"] == "completed"
    assert payload["summary_refresh"]["ok"] is True


def test_opl_module_healthcheck_uses_install_readiness_surface() -> None:
    script = _read("scripts/opl-module-healthcheck.sh")

    assert "scripts/verify.sh" not in script
    assert "uv run pytest" not in script
    assert 'command -v uv >/dev/null 2>&1' in script
    assert 'ds_bin="$(command -v ds)"' in script
    assert '"${ds_bin}" --help >/dev/null' in script
    assert "uv run python - <<'PY'" in script
    assert "from deepscientist.home import repo_root as resolved_repo_root" in script
    assert "from deepscientist.skills import discover_skill_bundles" in script
    assert '"src" / "skills" / "scout" / "SKILL.md"' in script
    assert '"src" / "skills" / "figure-polish" / "SKILL.md"' in script
