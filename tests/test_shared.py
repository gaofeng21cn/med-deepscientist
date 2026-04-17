from __future__ import annotations

import os
import time
from pathlib import Path

from deepscientist import shared
from deepscientist.shared import write_json


def test_resolve_runner_binary_prefers_env_override_for_codex(monkeypatch, tmp_path: Path) -> None:
    system_codex = tmp_path / "system-codex"
    system_codex.write_text("", encoding="utf-8")
    override_codex = tmp_path / "override-codex"
    override_codex.write_text("", encoding="utf-8")

    def fake_resolve(reference: str) -> str | None:
        if reference == "codex":
            return str(system_codex)
        if reference == str(override_codex):
            return str(override_codex)
        return None

    monkeypatch.setattr(shared, "_resolve_executable_reference", fake_resolve)
    monkeypatch.setenv("DEEPSCIENTIST_CODEX_BINARY", str(override_codex))

    assert shared.resolve_runner_binary("codex", runner_name="codex") == str(override_codex)


def test_resolve_runner_binary_prefers_path_codex_over_bundled_fallback(monkeypatch, tmp_path: Path) -> None:
    system_codex = tmp_path / "system-codex"
    system_codex.write_text("", encoding="utf-8")
    bundled_root = tmp_path / "repo"
    bundled_binary = bundled_root / "node_modules" / ".bin" / "codex"
    bundled_binary.parent.mkdir(parents=True, exist_ok=True)
    bundled_binary.write_text("", encoding="utf-8")

    monkeypatch.delenv("DEEPSCIENTIST_CODEX_BINARY", raising=False)
    monkeypatch.delenv("DS_CODEX_BINARY", raising=False)
    monkeypatch.setattr(
        shared,
        "_resolve_executable_reference",
        lambda reference: str(system_codex) if reference == "codex" else None,
    )
    monkeypatch.setattr(shared, "_codex_repo_roots", lambda: [bundled_root])

    assert shared.resolve_runner_binary("codex", runner_name="codex") == str(system_codex)


def test_resolve_runner_binary_uses_bundled_codex_as_fallback(monkeypatch, tmp_path: Path) -> None:
    bundled_root = tmp_path / "repo"
    bundled_binary = bundled_root / "node_modules" / ".bin" / "codex"
    bundled_binary.parent.mkdir(parents=True, exist_ok=True)
    bundled_binary.write_text("", encoding="utf-8")

    monkeypatch.delenv("DEEPSCIENTIST_CODEX_BINARY", raising=False)
    monkeypatch.delenv("DS_CODEX_BINARY", raising=False)
    monkeypatch.setattr(shared, "_resolve_executable_reference", lambda reference: None)
    monkeypatch.setattr(shared, "_codex_repo_roots", lambda: [bundled_root])

    assert shared.resolve_runner_binary("codex", runner_name="codex") == str(bundled_binary)


def test_write_json_prunes_stale_atomic_tempfiles(tmp_path: Path) -> None:
    target = tmp_path / "details.v1.json"
    target.write_text('{"old": true}\n', encoding="utf-8")
    stale = tmp_path / "details.v1.json.deadbeef.tmp"
    stale.write_text("stale\n", encoding="utf-8")
    old = time.time() - 8 * 3600
    os.utime(stale, (old, old))

    write_json(target, {"fresh": True})

    assert not stale.exists()
    assert target.read_text(encoding="utf-8").strip() == '{\n  "fresh": true\n}'
