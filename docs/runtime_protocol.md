# MedDeepScientist Runtime Protocol (Stable Minimal Surface)

Status: `stable`  
Version: `v1`  
Applies to: `MedAutoScience -> MedDeepScientist` runtime adapter contract

## 1. Scope

This document defines the only stable runtime surface that `MedAutoScience` may depend on by default:

- daemon API shape (minimal subset)
- quest/worktree filesystem layout
- startup/turn runtime contract

Anything not listed here is non-stable product surface.

## 2. Stable Daemon API Shape

Only the following HTTP routes and payload shape are stable for adapter integration.

### 2.1 Liveness and identity

- `GET /api/health`
- Stable response keys:
  - `status` (`"ok"` when healthy)
  - `home` (absolute runtime home)
  - `daemon_id`
  - `managed_by`
  - `pid`
  - `sessions` (current session snapshot object)

### 2.2 Quest creation and snapshot

- `POST /api/quests`
- Stable request fields:
  - required: `goal` (non-empty string)
  - optional: `title`, `quest_id`, `source`, `startup_contract`, `requested_baseline_ref`, `auto_start`, `initial_message`
- Stable success shape:
  - top-level `ok: true`
  - top-level `snapshot` object
  - if `auto_start=true`, top-level `startup` may be returned
- Stable failure shape:
  - top-level `ok: false`
  - top-level `message`
  - HTTP status may be `400` or `409` for contract/state errors

- `GET /api/quests/{quest_id}`
- Stable snapshot keys (minimum):
  - `quest_id`
  - `quest_root` (absolute path)
  - `status`
  - `active_anchor`
  - `baseline_gate`
  - `startup_contract`
  - `requested_baseline_ref`
  - `confirmed_baseline_ref`

### 2.3 Runtime-driving quest APIs

- `POST /api/quests/{quest_id}/control`
  - stable input: `action` (required), `source` (required)
  - stable output minimum: `ok`, `quest_id`, `status`

- `POST /api/quests/{quest_id}/chat`
  - stable input: `text` (required), `source` (optional)
  - stable output minimum: `ok`, plus queue/scheduling acknowledgement fields

- `GET /api/quests/{quest_id}/events`
  - stable output minimum: append-only event stream payload with `events` and cursor metadata

- `GET /api/quests/{quest_id}/workflow`
  - stable output minimum:
    - workflow projection payload
    - `projection_status`
    - `optimization_frontier` (may be `null` while projection not ready)

## 3. Stable Quest/Worktree Layout

Each quest is one Git repository rooted at `quest_root`.

Stable quest root files:

- `quest.yaml`
- `brief.md`
- `plan.md`
- `status.md`
- `SUMMARY.md`

Stable runtime directories:

- `baselines/imported/`
- `baselines/local/`
- `experiments/main/`
- `experiments/analysis/`
- `paper/`
- `memory/`
- `literature/`
- `handoffs/`
- `.ds/runs/`
- `.ds/worktrees/`
- `.ds/codex_history/`

Stable workspace semantics:

- active branch workspaces live under `.ds/worktrees/<worktree_id>/`
- `current_workspace_root` and `research_head_worktree_root` (when present) must resolve to quest-owned workspace paths
- binary/document resolution for active worktree must use `current_workspace_root` first

## 4. Stable Startup Contract

`startup_contract` is durable quest state stored in `quest.yaml` and returned in quest snapshots.

Stable guarantees:

- it is accepted as an object in `POST /api/quests`
- it is persisted and returned in snapshot payloads
- runtime turn policy may read these keys:
  - `need_research_paper`
  - `launch_mode`
  - `standard_profile`
  - `custom_profile`
  - `baseline_execution_policy`
  - `review_followup_policy`
  - `manuscript_edit_mode`
  - `decision_policy`

Keys not interpreted by runtime logic are treated as opaque metadata and must not break quest creation.

## 5. Stable Turn Contract

Turn execution must preserve a minimal runtime-to-runner contract.

Stable run request fields:

- `quest_id`
- `quest_root`
- `worktree_root`
- `run_id`
- `skill_id`
- `message`
- `model`
- `approval_policy`
- `sandbox_mode`
- `turn_reason`
- `turn_intent`
- `turn_mode`

Stable `turn_reason` semantics:

- `user_message`: user-originated turn
- `auto_continue`: daemon-originated continuation turn with no new user message
- `queued_user_messages`: daemon turn resumed from queued mailbox messages

Stable turn routing guarantees:

- structured bootstrap payloads that match the documented bootstrap shape must classify as stage continuation instead of direct Q&A
- bootstrap field questions must remain user questions rather than being misclassified as structured bootstrap
- if `baseline_gate=pending`, `review_audit -> review` and `revision_rebuttal -> rebuttal` remain valid direct continuation entries
- if the candidate continuation skill is `experiment` but there is no durable `active_idea_id`, runtime must gate to `idea` when `need_research_paper=true`, otherwise gate to `optimize`

Stable prompt contract:

- prompt must include a `## Turn Driver` block
- that block must encode at least `turn_reason`
- for `user_message` turns, it must encode `turn_intent` and `turn_mode`
- for `auto_continue` turns, it must explicitly state that there is no new user message and continuation uses durable state

## 6. Explicit Non-Stable Product Surfaces

The following are intentionally non-stable unless promoted into this spec:

- all daemon routes not listed in Section 2
- connector-specific transport/product behavior details (QQ, Weixin, Lingzhu, WhatsApp, Telegram, etc.)
- UI/TUI rendering payload details
- prompt prose outside the minimal Turn Driver contract in Section 5
- stage skill internals and non-contract wording
- optional product APIs (`/api/v1/*`, docs/latex/annotation/arxiv admin surfaces)
- experimental projection detail fields beyond the minimal keys listed above

## 7. Change Control

No intake/fix/refactor may silently break this stable protocol.

Any change to stable behavior requires all of:

1. update this spec in the same change
2. update or add targeted regression tests
3. keep README and AGENTS references aligned with this document
