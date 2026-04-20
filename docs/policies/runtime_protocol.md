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
- `requested_baseline_ref` create-time semantics:
  - if supplied and quest creation succeeds, runtime has already attempted baseline materialization plus baseline confirmation
  - successful create therefore implies the quest snapshot may already carry `baseline_gate=confirmed` and `confirmed_baseline_ref`
  - if requested baseline materialization fails, quest creation fails with `409` and the quest root must not remain on disk

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

### 2.3 Startup context patch

- `PATCH /api/quests/{quest_id}/startup-context`
- Stable request fields:
  - at least one of `startup_contract` or `requested_baseline_ref`
  - both fields accept object or `null`
- Stable success shape:
  - top-level `ok: true`
  - top-level `quest_id`
  - top-level `snapshot` object
- `requested_baseline_ref` patch-time semantics:
  - patch only updates durable quest metadata and snapshot echo
  - patch does not materialize or confirm baselines by itself
  - successful patch must not be interpreted as baseline attachment or `baseline_gate` promotion

### 2.4 Quest session and runtime audit

- `GET /api/quests/{quest_id}/session`
- Stable output minimum:
  - top-level `ok: true`
  - top-level `quest_id`
  - top-level `snapshot`
  - top-level `runtime_audit`
  - top-level `acp_session`
- Stable native runtime truth extension:
  - top-level `runtime_event_ref` may be returned when a quest-owned native runtime event has already been materialized
  - top-level `runtime_event` may be returned as the latest native runtime event payload
  - if present, `runtime_event_ref` and `runtime_event` must point to the same durable artifact
- Stable `runtime_audit` keys:
  - `ok`
  - `status` (`live` or `none`)
  - `source`
  - `active_run_id`
  - `worker_running`
  - `worker_pending`
  - `stop_requested`

- `GET /api/quests/{quest_id}/bash/sessions`
- Stable list entry minimum:
  - `bash_id`
  - `status`

### 2.5 Runtime-driving quest APIs

- `POST /api/quests/{quest_id}/control`
  - stable input: `action` (required), `source` (required)
  - stable output minimum: `ok`, `quest_id`, `action`, `status`, `snapshot`

- `POST /api/quests/{quest_id}/chat`
  - stable input: `text` (required), `source` (optional)
  - optional typed decision input:
    - `reply_to_interaction_id`
    - `decision_response` object
    - for quest completion approval, `decision_response` may carry `{decision_type: "quest_completion_approval", approved: true|false}`
  - stable output minimum: `ok`, plus queue/scheduling acknowledgement fields

- `POST /api/quests/{quest_id}/artifact/complete`
  - stable input: `summary` (required)
  - stable output minimum: `ok`, `status`, `snapshot`, `summary_refresh`
  - completion approval semantics:
    - runtime first looks for a blocking completion request whose `reply_schema.decision_type == "quest_completion_approval"`
    - the replying user message must carry `reply_to_interaction_id`
    - the replying user message must carry typed `decision_response = {decision_type: "quest_completion_approval", approved: true}`

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

- `artifacts/reports/runtime_events/`
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

### 3.1 Stable Native Runtime Event Surface

When present, the quest-owned native runtime event surface is:

- `artifacts/reports/runtime_events/<timestamp>_<event_kind>.json`
- `artifacts/reports/runtime_events/latest.json`

Stable native runtime event payload minimum:

- `schema_version`
- `event_id`
- `quest_id`
- `emitted_at`
- `event_source`
- `event_kind`
- `summary_ref`
- `status_snapshot`
- `outer_loop_input`

Stable `status_snapshot` / `outer_loop_input` minimum keys:

- `quest_status`
- `display_status`
- `active_run_id`
- `runtime_liveness_status`
- `worker_running`
- `stop_reason`
- `continuation_policy`
- `continuation_reason`
- `pending_user_message_count`
- `interaction_action`
- `interaction_requires_user_input`
- `active_interaction_id`
- `last_transition_at`

Stable semantics:

- this is runtime-owned quest truth, not a controller-side projection
- `runtime_liveness_status` distinguishes at least `live`, `stale`, and `none`
- `waiting_for_user`, `paused`, `stopped`, stale-turn reconcile, and runner-error display states must be representable without collapsing back into a single healthy/inactive label
- `quest.runtime_event` may also appear in `.ds/events.jsonl` as the append-only pointer event for the durable artifact

## 4. Stable Startup Contract

`startup_contract` is durable quest state stored in `quest.yaml` and returned in quest snapshots.

Stable guarantees:

- it is accepted as an object in `POST /api/quests`
- it is persisted and returned in snapshot payloads
- runtime turn policy may read these keys:
  - `need_research_paper`
  - `control_mode`
  - `launch_mode`
  - `standard_profile`
  - `custom_profile`
  - `baseline_execution_policy`
  - `review_followup_policy`
  - `manuscript_edit_mode`
  - `decision_policy`
- the runtime-owned stable subset is:
  - `schema_version`
  - `user_language`
  - `need_research_paper`
  - `decision_policy`
  - `control_mode`
  - `launch_mode`
  - `standard_profile`
  - `custom_profile`
  - `baseline_execution_policy`
  - `review_followup_policy`
  - `manuscript_edit_mode`

`startup_contract.control_mode` is the runtime control surface for checkpoint autonomy:

- `autonomous`: ordinary safe checkpoints continue automatically unless another continuation rule or explicit wait reason takes precedence
- `copilot`: default runtime continuation is reconciled to `wait_for_user_or_resume` so the quest parks for human review between checkpoints

Controller-owned extensions are still allowed at the same flat level and must be durably persisted plus echoed back in snapshots. The authoritative stable extension set currently includes:

- `research_intensity`
- `scope`
- `baseline_mode`
- `resource_policy`
- `time_budget_hours`
- `git_strategy`
- `runtime_constraints`
- `objectives`
- `baseline_urls`
- `paper_urls`
- `entry_state_summary`
- `review_summary`
- `controller_first_policy_summary`
- `automation_ready_summary`
- `custom_brief`
- `required_first_anchor`
- `legacy_code_execution_allowed`
- `startup_boundary_gate`
- `runtime_reentry_gate`
- `journal_shortlist`
- `medical_analysis_contract_summary`
- `medical_reporting_contract_summary`
- `reporting_guideline_family`
- `submission_targets`

For these controller-owned extensions, the runtime contract only guarantees durable persistence and stable snapshot roundtrip by default. They are not promoted into the runtime-owned core semantic subset unless this spec is explicitly updated.

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
- `executor_kind`

Stable `executor_kind` semantics:

- default value is `codex_cli`
- explicit `executor_kind=hermes_native_proof` routes to the `HermesNativeProofRunner`
- `hermes_native_proof` is opt-in only; it must not silently replace the default `codex_cli` lane
- `hermes_native_proof` must fail closed unless a real full agent loop is proved through tool events plus a valid final object response

Stable runner lane semantics:

- default runner remains `codex`
- `hermes_native_proof` stays an opt-in proof lane
- `claude` and `opencode` stay reserved experimental runner ids
- provider-backed profiles stay on the Codex runner contract
- provider env sanitization for `requires_openai_auth = false` stays inside the Codex profile compatibility path
- connector-specific prompt wording stays in connector prompt fragments while runner/provider guidance stays outside connector prompt fragments

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
