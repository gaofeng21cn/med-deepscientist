from __future__ import annotations

from pathlib import Path

import pytest

from deepscientist.runners.base import HERMES_NATIVE_PROOF_EXECUTOR_KIND
from deepscientist.runners.hermes_native_proof import (
    HermesNativeProofDependencyError,
    read_hermes_agent_contract,
    run_hermes_native_exec,
)


def test_read_hermes_agent_contract_prefers_local_config_and_env_override() -> None:
    contract = read_hermes_agent_contract(
        env={"DEEPSCIENTIST_HERMES_REASONING_EFFORT": "xhigh"},
        runner_config={"provider": "custom"},
        config_loader=lambda: {
            "model": {
                "default": "gpt-5.4",
                "provider": "openai",
                "base_url": "https://example.test/v1",
                "api_mode": "responses",
            },
            "agent": {"reasoning_effort": "high"},
        },
        reasoning_parser=lambda value: {"value": value},
    )

    assert contract["model"] == "gpt-5.4"
    assert contract["provider"] == "custom"
    assert contract["base_url"] == "https://example.test/v1"
    assert contract["api_mode"] == "responses"
    assert contract["reasoning_effort"] == "xhigh"
    assert contract["resolution"]["model"] == "local_config"
    assert contract["resolution"]["reasoning_effort"] == "env_override"


def test_read_hermes_agent_contract_requires_default_model() -> None:
    with pytest.raises(HermesNativeProofDependencyError, match="缺少可执行 model"):
        read_hermes_agent_contract(
            config_loader=lambda: {"model": {}, "agent": {}},
            reasoning_parser=lambda value: value,
        )


def test_run_hermes_native_exec_requires_full_agent_loop_and_real_tool_events(tmp_path: Path) -> None:
    class FakeAgent:
        def __init__(self, **kwargs):  # noqa: ANN003
            self._kwargs = kwargs
            self.api_mode = "chat_completions"
            self.session_id = "session-001"

        def run_conversation(self, prompt: str) -> dict:
            self._kwargs["step_callback"](1, [])
            self._kwargs["tool_start_callback"]("tool-1", "read_file", {"path": "/tmp/input.json"})
            self._kwargs["tool_complete_callback"]("tool-1", "read_file", {"path": "/tmp/input.json"}, "ok")
            return {
                "completed": True,
                "api_calls": 2,
                "final_response": '{"answer":"done"}',
            }

        def close(self) -> None:
            return None

    cwd = tmp_path / "workspace"
    cwd.mkdir()
    contract, payload, proof = run_hermes_native_exec(
        "read the file first",
        cwd=cwd,
        config_loader=lambda: {
            "model": {"default": "gpt-5.4", "provider": "custom", "api_mode": "chat_completions"},
            "agent": {"reasoning_effort": "xhigh"},
        },
        reasoning_parser=lambda value: {"value": value},
        agent_factory=FakeAgent,
    )

    assert contract["model"] == "gpt-5.4"
    assert payload == {"answer": "done"}
    assert proof["executor_kind"] == HERMES_NATIVE_PROOF_EXECUTOR_KIND
    assert proof["full_agent_loop_proved"] is True
    assert proof["tool_call_count"] == 1
    assert proof["reasoning_semantics_status"] == "unproven_custom_chat_completions"


def test_run_hermes_native_exec_rejects_chat_only_result(tmp_path: Path) -> None:
    class FakeAgent:
        def __init__(self, **kwargs):  # noqa: ANN003
            self.api_mode = "responses"
            self.session_id = "session-002"

        def run_conversation(self, prompt: str) -> dict:
            return {
                "completed": True,
                "api_calls": 1,
                "final_response": "chat only",
            }

        def close(self) -> None:
            return None

    cwd = tmp_path / "workspace"
    cwd.mkdir()

    with pytest.raises(HermesNativeProofDependencyError, match="未触发任何工具事件"):
        run_hermes_native_exec(
            "chat only",
            cwd=cwd,
            config_loader=lambda: {"model": {"default": "gpt-5.4"}, "agent": {}},
            reasoning_parser=lambda value: value,
            agent_factory=FakeAgent,
        )
