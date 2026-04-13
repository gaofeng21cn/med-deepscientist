from __future__ import annotations

from .codex import CodexRunner
from .hermes_native_proof import HermesNativeProofRunner
from .registry import register_runner


def register_builtin_runners(
    *,
    codex_runner: CodexRunner,
    hermes_native_proof_runner: HermesNativeProofRunner,
) -> None:
    register_runner("codex", lambda **_: codex_runner)
    register_runner("hermes_native_proof", lambda **_: hermes_native_proof_runner)
