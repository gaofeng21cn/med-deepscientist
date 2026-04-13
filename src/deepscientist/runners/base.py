from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Any

DEFAULT_EXECUTOR_KIND = "codex_cli"
DEFAULT_EXECUTOR_ALIASES = {
    "",
    "codex",
    "codex_cli",
    "codex_cli_autonomous",
}
HERMES_NATIVE_PROOF_EXECUTOR_KIND = "hermes_native_proof"
HERMES_NATIVE_PROOF_RUNNER = "hermes_native_proof"


def normalize_executor_kind(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in DEFAULT_EXECUTOR_ALIASES:
        return DEFAULT_EXECUTOR_KIND if normalized else None
    if normalized == HERMES_NATIVE_PROOF_EXECUTOR_KIND:
        return HERMES_NATIVE_PROOF_EXECUTOR_KIND
    raise ValueError(
        f"Unknown executor_kind `{normalized}`. Supported values: `{DEFAULT_EXECUTOR_KIND}`, `{HERMES_NATIVE_PROOF_EXECUTOR_KIND}`."
    )


def resolve_runner_and_executor_kind(
    *,
    requested_runner: str | None,
    requested_executor_kind: str | None,
    default_runner: str = "codex",
) -> tuple[str, str]:
    normalized_runner = str(requested_runner or "").strip().lower() or None
    normalized_default_runner = str(default_runner or "codex").strip().lower() or "codex"
    normalized_executor_kind = normalize_executor_kind(requested_executor_kind)

    if normalized_runner is None:
        if normalized_executor_kind == HERMES_NATIVE_PROOF_EXECUTOR_KIND:
            return HERMES_NATIVE_PROOF_RUNNER, HERMES_NATIVE_PROOF_EXECUTOR_KIND
        if normalized_default_runner == HERMES_NATIVE_PROOF_RUNNER:
            return HERMES_NATIVE_PROOF_RUNNER, HERMES_NATIVE_PROOF_EXECUTOR_KIND
        return normalized_default_runner, DEFAULT_EXECUTOR_KIND

    if normalized_runner == HERMES_NATIVE_PROOF_RUNNER:
        if normalized_executor_kind in {None, HERMES_NATIVE_PROOF_EXECUTOR_KIND}:
            return HERMES_NATIVE_PROOF_RUNNER, HERMES_NATIVE_PROOF_EXECUTOR_KIND
        raise ValueError(
            f"Runner `{HERMES_NATIVE_PROOF_RUNNER}` 只能和 `{HERMES_NATIVE_PROOF_EXECUTOR_KIND}` 搭配使用。"
        )

    if normalized_executor_kind == HERMES_NATIVE_PROOF_EXECUTOR_KIND:
        raise ValueError(
            f"`executor_kind={HERMES_NATIVE_PROOF_EXECUTOR_KIND}` 需要配套 `{HERMES_NATIVE_PROOF_RUNNER}` runner。"
        )
    return normalized_runner, DEFAULT_EXECUTOR_KIND


@dataclass(frozen=True)
class RunRequest:
    quest_id: str
    quest_root: Path
    worktree_root: Path | None
    run_id: str
    skill_id: str
    message: str
    model: str
    approval_policy: str
    sandbox_mode: str
    turn_reason: str = "user_message"
    turn_intent: str = "continue_stage"
    turn_mode: str = "stage_execution"
    reasoning_effort: str | None = None
    executor_kind: str = DEFAULT_EXECUTOR_KIND
    turn_id: str | None = None
    attempt_index: int = 1
    max_attempts: int = 1
    retry_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class RunResult:
    ok: bool
    run_id: str
    model: str
    output_text: str
    exit_code: int
    history_root: Path
    run_root: Path
    stderr_text: str
    proof: dict[str, Any] | None = None
