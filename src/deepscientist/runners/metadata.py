from __future__ import annotations

from dataclasses import dataclass

STABLE_DEFAULT_CONTRACT = "stable_default"
OPT_IN_PROOF_CONTRACT = "opt_in_proof"
RESERVED_EXPERIMENTAL_CONTRACT = "reserved_experimental"


@dataclass(frozen=True)
class RunnerMetadata:
    name: str
    label: str
    default_binary: str
    default_config_dir: str
    contract_lane: str
    runnable: bool
    supports_provider_profile: bool = False
    supports_reasoning_effort: bool = False


_RUNNER_METADATA: dict[str, RunnerMetadata] = {
    "codex": RunnerMetadata(
        name="codex",
        label="Codex",
        default_binary="codex",
        default_config_dir="~/.codex",
        contract_lane=STABLE_DEFAULT_CONTRACT,
        runnable=True,
        supports_provider_profile=True,
        supports_reasoning_effort=True,
    ),
    "hermes_native_proof": RunnerMetadata(
        name="hermes_native_proof",
        label="Hermes Native Proof",
        default_binary="",
        default_config_dir="~/.hermes",
        contract_lane=OPT_IN_PROOF_CONTRACT,
        runnable=True,
        supports_provider_profile=False,
        supports_reasoning_effort=True,
    ),
    "claude": RunnerMetadata(
        name="claude",
        label="Claude",
        default_binary="claude",
        default_config_dir="~/.claude",
        contract_lane=RESERVED_EXPERIMENTAL_CONTRACT,
        runnable=False,
        supports_provider_profile=False,
        supports_reasoning_effort=False,
    ),
    "opencode": RunnerMetadata(
        name="opencode",
        label="OpenCode",
        default_binary="opencode",
        default_config_dir="~/.config/opencode",
        contract_lane=RESERVED_EXPERIMENTAL_CONTRACT,
        runnable=False,
        supports_provider_profile=False,
        supports_reasoning_effort=False,
    ),
}


def get_runner_metadata(name: str) -> RunnerMetadata:
    normalized = str(name or "").strip().lower()
    try:
        return _RUNNER_METADATA[normalized]
    except KeyError as exc:
        available = ", ".join(sorted(_RUNNER_METADATA)) or "none"
        raise KeyError(f"Unknown runner `{normalized}`. Available runners: {available}.") from exc


def list_runner_metadata_names() -> tuple[str, ...]:
    return tuple(_RUNNER_METADATA)


def list_reserved_experimental_runner_names() -> tuple[str, ...]:
    return tuple(
        name
        for name, metadata in _RUNNER_METADATA.items()
        if metadata.contract_lane == RESERVED_EXPERIMENTAL_CONTRACT
    )


def runner_capabilities(name: str) -> dict[str, bool]:
    metadata = get_runner_metadata(name)
    return {
        "provider_profile": metadata.supports_provider_profile,
        "reasoning_effort": metadata.supports_reasoning_effort,
        "env_sanitization": metadata.supports_provider_profile and metadata.name == "codex",
        "full_agent_proof": metadata.contract_lane == OPT_IN_PROOF_CONTRACT,
    }

