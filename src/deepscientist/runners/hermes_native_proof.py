from __future__ import annotations

import importlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Callable

from ..artifact import ArtifactService
from ..gitops import export_git_graph
from ..prompts import PromptBuilder
from ..runtime_logs import JsonlLogger
from ..shared import append_jsonl, ensure_dir, generate_id, utc_now, write_json, write_text
from .base import HERMES_NATIVE_PROOF_EXECUTOR_KIND, RunRequest, RunResult

ConfigLoader = Callable[[], dict[str, Any]]
ReasoningParser = Callable[[str], Any]
AgentFactory = Callable[..., Any]


class HermesNativeProofDependencyError(RuntimeError):
    """真实上游 Hermes-Agent 依赖不可用。"""


class HermesNativeProofRunner:
    def __init__(
        self,
        *,
        home: Path,
        repo_root: Path,
        logger: JsonlLogger,
        prompt_builder: PromptBuilder,
        artifact_service: ArtifactService,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.home = home
        self.repo_root = repo_root
        self.logger = logger
        self.prompt_builder = prompt_builder
        self.artifact_service = artifact_service
        self.config = dict(config or {})
        self._active_agent_lock = threading.Lock()
        self._active_agents: dict[str, Any] = {}

    def run(self, request: RunRequest) -> RunResult:
        workspace_root = request.worktree_root or request.quest_root
        run_root = ensure_dir(request.quest_root / ".ds" / "runs" / request.run_id)
        history_root = ensure_dir(request.quest_root / ".ds" / "hermes_history" / request.run_id)
        prompt = self.prompt_builder.build(
            quest_id=request.quest_id,
            skill_id=request.skill_id,
            user_message=request.message,
            model=request.model,
            turn_reason=request.turn_reason,
            turn_intent=request.turn_intent,
            turn_mode=request.turn_mode,
            retry_context=request.retry_context,
        )
        write_text(run_root / "prompt.md", prompt)
        prompt_file = run_root / "hermes_prompt.md"
        write_text(prompt_file, prompt)

        proof_request = _build_proof_request(
            prompt_file=prompt_file,
            quest_root=request.quest_root,
            workspace_root=workspace_root,
        )
        write_text(run_root / "hermes_request.md", proof_request)

        quest_events = request.quest_root / ".ds" / "events.jsonl"
        append_jsonl(
            quest_events,
            {
                "event_id": generate_id("evt"),
                "type": "runner.turn_start",
                "quest_id": request.quest_id,
                "run_id": request.run_id,
                "source": HERMES_NATIVE_PROOF_EXECUTOR_KIND,
                "skill_id": request.skill_id,
                "model": request.model,
                "executor_kind": request.executor_kind,
                "created_at": utc_now(),
            },
        )

        contract, payload, proof = run_hermes_native_exec(
            proof_request,
            cwd=workspace_root,
            runner_config=self.config,
            register_active_agent=lambda agent: self._register_active_agent(request.quest_id, agent),
            unregister_active_agent=lambda: self._unregister_active_agent(request.quest_id),
        )
        output_text = _render_output_text(payload)
        stderr_text = ""

        write_text(history_root / "assistant.md", (output_text + "\n") if output_text else "")
        write_text(run_root / "stderr.txt", stderr_text)
        write_json(run_root / "proof.json", proof)
        write_json(
            history_root / "events.json",
            {
                "contract": contract,
                "proof": proof,
            },
        )
        for event in _quest_events_from_proof(
            quest_id=request.quest_id,
            run_id=request.run_id,
            skill_id=request.skill_id,
            created_at=utc_now(),
            proof=proof,
        ):
            append_jsonl(quest_events, event)
        append_jsonl(
            quest_events,
            {
                "event_id": generate_id("evt"),
                "type": "runner.agent_message",
                "quest_id": request.quest_id,
                "run_id": request.run_id,
                "source": HERMES_NATIVE_PROOF_EXECUTOR_KIND,
                "skill_id": request.skill_id,
                "text": output_text,
                "created_at": utc_now(),
            },
        )
        append_jsonl(
            quest_events,
            {
                "event_id": generate_id("evt"),
                "type": "runner.turn_finish",
                "quest_id": request.quest_id,
                "run_id": request.run_id,
                "source": HERMES_NATIVE_PROOF_EXECUTOR_KIND,
                "skill_id": request.skill_id,
                "model": contract["model"],
                "executor_kind": request.executor_kind,
                "exit_code": 0,
                "stderr_text": "",
                "summary": output_text[:1000],
                "created_at": utc_now(),
            },
        )

        result_payload = {
            "ok": True,
            "run_id": request.run_id,
            "model": contract["model"],
            "exit_code": 0,
            "history_root": str(history_root),
            "run_root": str(run_root),
            "output_text": output_text,
            "stderr_text": "",
            "executor_kind": request.executor_kind,
            "proof": proof,
            "completed_at": utc_now(),
        }
        write_json(run_root / "result.json", result_payload)
        write_json(history_root / "meta.json", result_payload)
        artifact_result = self.artifact_service.record(
            request.quest_root,
            {
                "kind": "run",
                "status": "completed",
                "run_id": request.run_id,
                "run_kind": request.skill_id,
                "model": contract["model"],
                "summary": output_text[:1000],
                "history_root": str(history_root),
                "run_root": str(run_root),
                "exit_code": 0,
                "executor_kind": request.executor_kind,
            },
            workspace_root=workspace_root,
            commit_message=f"run: {request.skill_id} {request.run_id}",
        )
        export_git_graph(request.quest_root, request.quest_root / "artifacts" / "graphs")
        write_json(run_root / "artifact.json", artifact_result)
        self.logger.log(
            "info",
            "runner.hermes_native_proof.completed",
            quest_id=request.quest_id,
            run_id=request.run_id,
            model=contract["model"],
            executor_kind=request.executor_kind,
        )
        return RunResult(
            ok=True,
            run_id=request.run_id,
            model=contract["model"],
            output_text=output_text,
            exit_code=0,
            history_root=history_root,
            run_root=run_root,
            stderr_text="",
            proof=proof,
        )

    def interrupt(self, quest_id: str) -> bool:
        with self._active_agent_lock:
            agent = self._active_agents.get(quest_id)
        if agent is None:
            return False
        for method_name in ("close", "request_stop", "stop"):
            method = getattr(agent, method_name, None)
            if callable(method):
                method()
                return True
        return False

    def _register_active_agent(self, quest_id: str, agent: Any) -> None:
        with self._active_agent_lock:
            self._active_agents[quest_id] = agent

    def _unregister_active_agent(self, quest_id: str) -> None:
        with self._active_agent_lock:
            self._active_agents.pop(quest_id, None)


def read_hermes_agent_contract(
    *,
    env: dict[str, str] | None = None,
    runner_config: dict[str, Any] | None = None,
    config_loader: ConfigLoader | None = None,
    reasoning_parser: ReasoningParser | None = None,
) -> dict[str, Any]:
    resolved_env = env or os.environ
    resolved_runner_config = dict(runner_config or {})
    loader = config_loader or _load_hermes_config_loader()
    parse_reasoning = reasoning_parser or _load_reasoning_parser()

    config = loader() if callable(loader) else {}
    model_config = config.get("model", {}) if isinstance(config.get("model"), dict) else {}
    agent_config = config.get("agent", {}) if isinstance(config.get("agent"), dict) else {}

    default_model = _normalize_model_default(model_config)
    default_provider = _normalize_optional_text(model_config.get("provider"))
    default_base_url = _normalize_optional_text(model_config.get("base_url"))
    default_api_mode = _normalize_optional_text(model_config.get("api_mode"))
    default_reasoning = _normalize_optional_text(agent_config.get("reasoning_effort"))

    configured_model = _normalize_runner_value(resolved_runner_config.get("model"))
    configured_reasoning = _normalize_runner_value(resolved_runner_config.get("model_reasoning_effort"))
    configured_provider = _normalize_runner_value(resolved_runner_config.get("provider"))
    configured_base_url = _normalize_runner_value(resolved_runner_config.get("base_url"))
    configured_api_mode = _normalize_runner_value(resolved_runner_config.get("api_mode"))

    model_override = _normalize_optional_text(resolved_env.get("DEEPSCIENTIST_HERMES_MODEL"))
    provider_override = _normalize_optional_text(resolved_env.get("DEEPSCIENTIST_HERMES_PROVIDER"))
    base_url_override = _normalize_optional_text(resolved_env.get("DEEPSCIENTIST_HERMES_BASE_URL"))
    api_mode_override = _normalize_optional_text(resolved_env.get("DEEPSCIENTIST_HERMES_API_MODE"))
    reasoning_override = _normalize_optional_text(resolved_env.get("DEEPSCIENTIST_HERMES_REASONING_EFFORT"))

    model = model_override or configured_model or default_model
    if model is None:
        raise HermesNativeProofDependencyError(
            "Hermes-native proof 缺少可执行 model：请在 `~/.hermes/config.yaml` 中提供 `model.default`，"
            "或显式设置 `DEEPSCIENTIST_HERMES_MODEL`。"
        )

    reasoning_effort = reasoning_override or configured_reasoning or default_reasoning
    return {
        "entrypoint": "run_agent.AIAgent.run_conversation",
        "full_agent_loop_required": True,
        "model": model,
        "provider": provider_override or configured_provider or default_provider,
        "base_url": base_url_override or configured_base_url or default_base_url,
        "api_mode": api_mode_override or configured_api_mode or default_api_mode,
        "reasoning_effort": reasoning_effort,
        "reasoning_config": parse_reasoning(reasoning_effort or ""),
        "resolution": {
            "model": "env_override" if model_override else ("runner_config" if configured_model else "local_config"),
            "reasoning_effort": "env_override"
            if reasoning_override
            else ("runner_config" if configured_reasoning else "local_config"),
        },
    }


def run_hermes_native_exec(
    prompt: str,
    *,
    cwd: str | Path,
    runner_config: dict[str, Any] | None = None,
    register_active_agent: Callable[[Any], None] | None = None,
    unregister_active_agent: Callable[[], None] | None = None,
    env: dict[str, str] | None = None,
    config_loader: ConfigLoader | None = None,
    reasoning_parser: ReasoningParser | None = None,
    agent_factory: AgentFactory | None = None,
) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    contract = read_hermes_agent_contract(
        env=env,
        runner_config=runner_config,
        config_loader=config_loader,
        reasoning_parser=reasoning_parser,
    )
    resolved_cwd = Path(cwd).expanduser().resolve()
    if not resolved_cwd.exists():
        raise HermesNativeProofDependencyError(f"Hermes-native proof working directory 不存在: {resolved_cwd}")

    agent_factory = agent_factory or _load_agent_factory()
    events: list[dict[str, Any]] = []

    def _append_event(event_type: str, **payload: Any) -> None:
        events.append({"type": event_type, **payload})

    agent = agent_factory(
        quiet_mode=True,
        model=contract["model"],
        provider=contract["provider"] or None,
        base_url=contract["base_url"] or None,
        api_mode=contract["api_mode"] or None,
        reasoning_config=contract["reasoning_config"],
        skip_context_files=True,
        skip_memory=True,
        tool_start_callback=lambda _tcid, name, args: _append_event("tool_start", tool=name, args=args),
        tool_complete_callback=lambda _tcid, name, _args, result: _append_event(
            "tool_complete",
            tool=name,
            result_preview=_preview_text(result),
        ),
        step_callback=lambda step_index, previous_tools: _append_event(
            "step",
            step=step_index,
            prev_tool_count=len(previous_tools),
        ),
        status_callback=lambda event_name, message: _append_event(
            "status",
            event=event_name,
            message=_preview_text(message),
        ),
        reasoning_callback=lambda text: _append_event("reasoning", preview=_preview_text(text)),
    )

    if callable(register_active_agent):
        register_active_agent(agent)
    try:
        result = agent.run_conversation(prompt)
    finally:
        if callable(unregister_active_agent):
            unregister_active_agent()
        close = getattr(agent, "close", None)
        if callable(close):
            close()

    if not isinstance(result, dict):
        raise HermesNativeProofDependencyError("Hermes-native proof 返回值必须是 object。")

    completed = bool(result.get("completed"))
    tool_start_events = [event for event in events if event["type"] == "tool_start"]
    tool_complete_events = [event for event in events if event["type"] == "tool_complete"]
    if not tool_start_events or not tool_complete_events:
        raise HermesNativeProofDependencyError("Hermes-native proof 未触发任何工具事件，不接受 chat-only 结果。")
    if not completed:
        raise HermesNativeProofDependencyError("Hermes-native proof 未完成完整 agent loop。")

    payload = _extract_final_response(result.get("final_response"))
    agent_api_mode = _normalize_optional_text(getattr(agent, "api_mode", None)) or contract["api_mode"]
    proof = {
        "proof_kind": "full_agent_loop_aiaagent",
        "entrypoint": contract["entrypoint"],
        "executor_kind": HERMES_NATIVE_PROOF_EXECUTOR_KIND,
        "full_agent_loop_proved": True,
        "session_id": _normalize_optional_text(getattr(agent, "session_id", None)),
        "model": contract["model"],
        "provider": contract["provider"],
        "api_mode": agent_api_mode,
        "reasoning_effort": contract["reasoning_effort"],
        "api_calls": _require_nonnegative_int(result, "api_calls"),
        "tool_call_count": len(tool_start_events),
        "event_count": len(events),
        "event_stream": events,
        "reasoning_semantics_status": _resolve_reasoning_status(
            provider=contract["provider"],
            api_mode=agent_api_mode,
        ),
    }
    return contract, payload, proof


def _build_proof_request(*, prompt_file: Path, quest_root: Path, workspace_root: Path) -> str:
    return "\n".join(
        [
            "You are running the MedDeepScientist Hermes-native experimental proof executor.",
            f"Use your file-reading tool to inspect this prompt file first: {prompt_file}",
            f"Quest root: {quest_root}",
            f"Workspace root: {workspace_root}",
            "After reading the prompt file, continue the task autonomously and produce the final assistant response as plain text only.",
            "Do not return tool logs, JSON wrappers, or markdown fences unless the prompt file explicitly asks for them.",
        ]
    )


def _quest_events_from_proof(
    *,
    quest_id: str,
    run_id: str,
    skill_id: str,
    created_at: str,
    proof: dict[str, Any],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for item in proof.get("event_stream") or []:
        event_type = str(item.get("type") or "").strip()
        if event_type == "tool_start":
            events.append(
                {
                    "event_id": generate_id("evt"),
                    "type": "runner.tool_call",
                    "quest_id": quest_id,
                    "run_id": run_id,
                    "source": HERMES_NATIVE_PROOF_EXECUTOR_KIND,
                    "skill_id": skill_id,
                    "tool_name": str(item.get("tool") or "").strip() or "unknown",
                    "args": json.dumps(item.get("args"), ensure_ascii=False),
                    "created_at": created_at,
                }
            )
        if event_type == "tool_complete":
            events.append(
                {
                    "event_id": generate_id("evt"),
                    "type": "runner.tool_result",
                    "quest_id": quest_id,
                    "run_id": run_id,
                    "source": HERMES_NATIVE_PROOF_EXECUTOR_KIND,
                    "skill_id": skill_id,
                    "tool_name": str(item.get("tool") or "").strip() or "unknown",
                    "status": "completed",
                    "output": str(item.get("result_preview") or "").strip(),
                    "created_at": created_at,
                }
            )
    return events


def _extract_final_response(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise HermesNativeProofDependencyError("Hermes-native proof 未返回 final response。")
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    raise HermesNativeProofDependencyError("Hermes-native proof final response 类型不合法。")


def _render_output_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _load_hermes_config_loader() -> ConfigLoader:
    module = _import_optional("hermes_cli.config")
    return getattr(module, "load_config")


def _load_reasoning_parser() -> ReasoningParser:
    module = _import_optional("hermes_constants")
    return getattr(module, "parse_reasoning_effort")


def _load_agent_factory() -> AgentFactory:
    module = _import_optional("run_agent")
    return getattr(module, "AIAgent")


def _import_optional(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise HermesNativeProofDependencyError(
            f"缺少上游 Hermes-Agent 依赖模块 `{module_name}`。请先在当前 Python 环境安装真实上游 Hermes-Agent。"
        ) from exc


def _normalize_model_default(payload: Any) -> str | None:
    if isinstance(payload, dict):
        return _normalize_optional_text(payload.get("default"))
    return _normalize_optional_text(payload)


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_runner_value(value: Any) -> str | None:
    text = _normalize_optional_text(value)
    if text in {None, "inherit", "inherit_local_hermes_default", "default"}:
        return None
    return text


def _preview_text(value: Any, limit: int = 240) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _require_nonnegative_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        raise HermesNativeProofDependencyError(f"Hermes-native proof 缺少合法的 `{key}`。")
    return value


def _resolve_reasoning_status(*, provider: str | None, api_mode: str | None) -> str:
    if provider == "custom" and api_mode == "chat_completions":
        return "unproven_custom_chat_completions"
    return "not_proved"
