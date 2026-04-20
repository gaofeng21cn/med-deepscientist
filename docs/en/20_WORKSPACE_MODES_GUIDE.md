# 20 Workspace Modes Guide

MedDeepScientist uses `Autonomous` and `Copilot` as user-facing checkpoint-autonomy labels while keeping runtime persistence on the fork-local `control_mode + continuation_policy` contract.

## Why This Guide Exists

Recent upstream work moved `workspace_mode` toward a runtime control field. This fork already uses `workspace_mode` for research/worktree state. Direct field-level intake would collapse two different authorities into one persisted field, so the safe path is semantic alignment rather than storage reuse.

## Local Contract

| Surface | Owner | Meaning |
| --- | --- | --- |
| `Autonomous` / `Copilot` labels | product, prompt, docs | User-facing checkpoint-autonomy vocabulary |
| `startup_contract.control_mode` | startup contract | Startup checkpoint-autonomy choice |
| `continuation_policy` / `continuation_reason` / `continuation_anchor` | runtime | Current continuation truth after startup, resume, recovery, or external-progress reconciliation |
| `workspace_mode` | research/worktree state | Research stage and layout namespace such as `quest`, `idea`, `analysis`, `paper`, `run`, `start_setup` |

## Semantic Mapping

### Startup rhythm

- `Autonomous` maps to `startup_contract.control_mode = autonomous`.
- `Copilot` maps to `startup_contract.control_mode = copilot`.
- Both modes can launch the first bounded task immediately. The difference appears at ordinary safe checkpoints.

### Continuation rhythm

- `control_mode = autonomous` means the default ordinary continuation state is `continuation_policy = auto`.
- `control_mode = copilot` means the default ordinary continuation state is `continuation_policy = wait_for_user_or_resume`.
- Explicit wait reasons, recovery state, supervisor ownership, and non-retryable errors still live in runtime-owned continuation fields and can override the startup default.
- Queued user messages always take priority over background continuation.
- When `continuation_anchor` is present, `/resume` continues from that recorded anchor instead of guessing a fresh stage.

### Background monitoring rhythm

- Detached long-running tasks still use progress-first monitoring with the standard cadence `60s -> 120s -> 300s -> 600s -> 1800s ...`.
- In `copilot`, the foreground quest may stay parked for human review while background monitoring keeps visibility and recovery checks alive.
- In `autonomous`, a healthy monitoring result may lead into the next safe action when no explicit blocker or approval boundary is active.
- Managed supervision or external-controller ownership should end the local watch loop after a checkpoint is recorded and reported.

## Operational Reading

### `Autonomous`

Use this wording when the quest should keep moving across ordinary safe checkpoints.

Local reading:

- startup control: `control_mode = autonomous`
- default continuation: `auto`
- user gate: only real blockers, explicit approval boundaries, or stronger continuation rules should park the quest

### `Copilot`

Use this wording when the quest should hand control back after each bounded safe unit.

Local reading:

- startup control: `control_mode = copilot`
- default continuation: `wait_for_user_or_resume`
- user gate: checkpoint review is the default handoff, while low-frequency monitoring can still continue in the background

## Invariants

- Keep `workspace_mode` reserved for research/worktree semantics.
- Keep checkpoint autonomy on `startup_contract.control_mode`.
- Keep runtime continuation truth on `continuation_policy`, `continuation_reason`, and `continuation_anchor`.
- Align wording, prompts, and docs with upstream meaning without copying the upstream `workspace_mode` persistence model into this fork.
