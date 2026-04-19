from __future__ import annotations

import deepscientist.codex_cli_compat as codex_cli_compat


def test_parse_codex_cli_version_extracts_semver() -> None:
    assert codex_cli_compat.parse_codex_cli_version("codex-cli 0.57.0") == (0, 57, 0)
    assert codex_cli_compat.parse_codex_cli_version("Codex-CLI 0.116.0\n") == (0, 116, 0)
    assert codex_cli_compat.parse_codex_cli_version("not a version") is None


def test_normalize_codex_reasoning_effort_downgrades_xhigh_for_legacy_cli(monkeypatch) -> None:
    codex_cli_compat.codex_cli_version.cache_clear()
    monkeypatch.setattr(codex_cli_compat, "codex_cli_version", lambda binary: (0, 57, 0))

    reasoning_effort, warning = codex_cli_compat.normalize_codex_reasoning_effort(
        "xhigh",
        resolved_binary="/tmp/fake-codex",
    )

    assert reasoning_effort == "high"
    assert warning is not None
    assert "0.57.0" in warning


def test_normalize_codex_reasoning_effort_keeps_xhigh_for_supported_cli(monkeypatch) -> None:
    codex_cli_compat.codex_cli_version.cache_clear()
    monkeypatch.setattr(codex_cli_compat, "codex_cli_version", lambda binary: (0, 116, 0))

    reasoning_effort, warning = codex_cli_compat.normalize_codex_reasoning_effort(
        "xhigh",
        resolved_binary="/tmp/fake-codex",
    )

    assert reasoning_effort == "xhigh"
    assert warning is None


def test_adapt_profile_only_provider_config_promotes_model_and_provider() -> None:
    config = """
[model_providers.minimax]
name = "MiniMax Chat Completions API"
base_url = "https://api.minimaxi.com/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "chat"
requires_openai_auth = false

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""".strip()

    adapted, warning = codex_cli_compat.adapt_profile_only_provider_config(config, profile="m27")

    assert warning is not None
    assert 'model_provider = "minimax"' in adapted
    assert 'model = "MiniMax-M2.7"' in adapted


def test_adapt_profile_only_provider_config_is_noop_when_top_level_fields_match_profile() -> None:
    config = """
model = "MiniMax-M2.7"
model_provider = "minimax"

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""".strip()

    adapted, warning = codex_cli_compat.adapt_profile_only_provider_config(config, profile="m27")

    assert adapted == config
    assert warning is None


def test_adapt_profile_only_provider_config_overrides_conflicting_top_level_fields() -> None:
    config = """
model = "gpt-5.4"
model_provider = "OpenAI"
model_reasoning_effort = "xhigh"

[model_providers.minimax]
name = "MiniMax Chat Completions API"
base_url = "https://api.minimaxi.com/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "chat"
requires_openai_auth = false

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""".strip()

    adapted, warning = codex_cli_compat.adapt_profile_only_provider_config(config, profile="m27")

    assert warning is not None
    assert "overrode conflicting top-level" in warning
    header = adapted.split("[model_providers.minimax]", 1)[0]
    assert 'model_provider = "minimax"' in header
    assert 'model = "MiniMax-M2.7"' in header
    assert 'model_provider = "OpenAI"' not in adapted
    assert 'model = "gpt-5.4"' not in adapted
    assert 'model_reasoning_effort = "xhigh"' in adapted


def test_provider_profile_metadata_reads_profile_provider_shape() -> None:
    config = """
[model_providers.minimax]
name = "MiniMax Chat Completions API"
base_url = "https://api.minimaxi.com/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "chat"
requires_openai_auth = false

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""".strip()

    metadata = codex_cli_compat.provider_profile_metadata(config, profile="m27")

    assert metadata == {
        "provider": "minimax",
        "model": "MiniMax-M2.7",
        "env_key": "MINIMAX_API_KEY",
        "base_url": "https://api.minimaxi.com/v1",
        "wire_api": "chat",
        "requires_openai_auth": False,
    }


def test_materialize_codex_runtime_home_syncs_source_and_quest_overlays(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source_home = tmp_path / "source-codex-home"
    source_home.mkdir()
    (source_home / "config.toml").write_text("[profiles.m27]\n", encoding="utf-8")
    (source_home / "auth.json").write_text('{"provider":"custom"}', encoding="utf-8")
    (source_home / "skills" / "global").mkdir(parents=True)
    (source_home / "skills" / "global" / "SKILL.md").write_text("GLOBAL SKILL\n", encoding="utf-8")
    (source_home / "agents").mkdir()
    (source_home / "agents" / "global-agent.md").write_text("GLOBAL AGENT\n", encoding="utf-8")
    (source_home / "prompts").mkdir()
    (source_home / "prompts" / "system.md").write_text("GLOBAL SYSTEM\n", encoding="utf-8")
    (source_home / "prompts" / "extra.md").write_text("GLOBAL EXTRA\n", encoding="utf-8")

    quest_codex = tmp_path / "quest" / ".codex"
    (quest_codex / "skills" / "quest").mkdir(parents=True)
    (quest_codex / "skills" / "quest" / "SKILL.md").write_text("QUEST SKILL\n", encoding="utf-8")
    (quest_codex / "prompts").mkdir()
    (quest_codex / "prompts" / "system.md").write_text("QUEST SYSTEM\n", encoding="utf-8")

    target_home = tmp_path / "quest" / ".ds" / "codex_homes" / "run-001"
    (target_home / "agents").mkdir(parents=True)
    (target_home / "agents" / "stale-agent.md").write_text("STALE\n", encoding="utf-8")
    (target_home / "skills" / "stale").mkdir(parents=True)
    (target_home / "skills" / "stale" / "SKILL.md").write_text("STALE\n", encoding="utf-8")
    (target_home / "prompts").mkdir(parents=True, exist_ok=True)
    (target_home / "prompts" / "stale.md").write_text("STALE\n", encoding="utf-8")

    warning = codex_cli_compat.materialize_codex_runtime_home(
        source_home=source_home,
        target_home=target_home,
        quest_codex_root=quest_codex,
    )

    assert warning is None
    assert (target_home / "config.toml").read_text(encoding="utf-8") == "[profiles.m27]\n"
    assert (target_home / "auth.json").read_text(encoding="utf-8") == '{"provider":"custom"}'
    assert (target_home / "skills" / "global" / "SKILL.md").read_text(encoding="utf-8") == "GLOBAL SKILL\n"
    assert (target_home / "skills" / "quest" / "SKILL.md").read_text(encoding="utf-8") == "QUEST SKILL\n"
    assert (target_home / "agents" / "global-agent.md").read_text(encoding="utf-8") == "GLOBAL AGENT\n"
    assert (target_home / "prompts" / "system.md").read_text(encoding="utf-8") == "QUEST SYSTEM\n"
    assert (target_home / "prompts" / "extra.md").read_text(encoding="utf-8") == "GLOBAL EXTRA\n"
    assert not (target_home / "agents" / "stale-agent.md").exists()
    assert not (target_home / "skills" / "stale").exists()
    assert not (target_home / "prompts" / "stale.md").exists()
