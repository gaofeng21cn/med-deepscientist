# MedDeepScientist Freeze Baseline

- public_project_name: `MedDeepScientist`
- engine_id: `med-deepscientist`
- engine_family: `MedDeepScientist`
- compatibility_runtime_names: Python package `deepscientist`, CLI `ds`, npm package `@researai/deepscientist`
- freeze_mode: `thin_fork`
- upstream_repo: `https://github.com/ResearAI/DeepScientist`
- upstream_base_commit: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- canonical_fork_remote: `origin -> git@github.com:gaofeng21cn/med-deepscientist.git`
- canonical_upstream_remote: `upstream -> git@github.com:ResearAI/DeepScientist.git`
- phase: `phase1_runtime_freeze`
- package_rename_applied: `false`
- daemon_api_shape_preserved: `true`
- quest_layout_preserved: `true`
- worktree_layout_preserved: `true`

MedDeepScientist (`med-deepscientist` 仓库) is a controlled fork used as the stable runtime layer under `MedAutoScience`.
It exists to preserve long-running quest execution, daemon compatibility, and auditable runtime behavior while upstream `DeepScientist` continues to evolve on its own cadence.

Remote semantics are explicit:

- `origin` is the canonical MedDeepScientist (`med-deepscientist`) GitHub repository
- `upstream` is the upstream `DeepScientist` repository used for intake comparison
- controlled-fork upgrade checks compare against `upstream/main`, not against the fork's own `origin/main`

## Applied Patchset

### Phase 1 runtime bugfix

- commit: `d4994dba3ae1720a60daa7c80f5043f3722f32d8`
- kind: `runtime_bugfix`
- reason: `document_asset` must resolve path documents from the active worktree so Web App previews for PNG / SVG / PDF remain correct.
- verification: `PYTHONPATH=src pytest -q tests/test_daemon_api.py -k 'document_asset_resolves_path_documents_from_active_worktree'`

### Round 1 upstream intake runtime bugfix

- commit: `bf97bfbf3fa4119924b10e2ff2c9edabece0b402`
- kind: `runtime_bugfix`
- reason: bootstrap quests must not be misclassified as direct questions, and stage routing must not enter `experiment` before a durable `idea` or `optimize` anchor exists.
- verification:
  - `rtk uv run pytest -q tests/test_daemon_api.py -k 'classify_turn_intent_prefers_continue_stage_for_structured_bootstrap or turn_skill_for_rejects_experiment_without_durable_idea_in_algorithm_first or turn_skill_for_rejects_experiment_without_durable_idea_in_paper_mode'`
  - `rtk uv run pytest -q tests/test_prompt_builder.py -k 'does_not_misclassify_structured_bootstrap_as_direct_question'`

### Round 2 upstream intake runtime and launcher hardening

- local_commit: `ec845f3`
- upstream_commit: `01b8901d0066cce3a598e0185d861b88c6f571b9`
- kind: `runtime_bugfix`
- reason: `bash_exec` MCP payloads now accept list-wrapped commands, matching newer upstream tool-call shapes without changing the MAS runtime protocol.
- verification: `uv run pytest -q tests/test_mcp_servers.py -k "bash_exec_mcp_server_normalizes_list_wrapped_commands or bash_exec_mcp_server_supports_detach_read_list_and_kill"`

- local_commit: `b928098`
- upstream_bundle:
  - `5364b6212e276bb4cc2e6a0d9353ebc5f6cfbccb`
  - `1a5333c2e629471ff1100b113ac67f28bc7a3288`
  - `be386ae912b9d496edf6d46982ff280083ab6dbf`
  - `e41f6a798298f8854607dbe9a885bd1b5b8d074b`
  - `af8d0e263bc7fcd0721318e1d4b3cdb26a1b6ce3`
- kind: `runtime_bugfix`
- reason: queued user messages now recover genuinely stalled live turns, preserve later pause/stop intent, emit runtime reconciliation events, and keep runtime storage maintenance on the recovery path.
- verification:
  - `uv run pytest -q tests/test_daemon_api.py`
  - `uv run pytest -q tests/test_daemon_api.py -k "stale_active_turn or stale_live_turn or auto_resumes_recent_reconciled_quest or auto_resume_old_reconciled_quest or quest_runtime_audit_reconciles_stale_live_turn"`

- local_commit: `6e60e3f`
- upstream_bundle:
  - `4f0975625c182f3b784c61921776f6c76d375951`
  - `a149a22b890d9bd5d487f9bb764aad6cabc5a79f`
- kind: `launcher_bugfix`
- reason: launcher self-update now resolves `npmBinary` reliably, and uv bootstrap strips Python / conda / mamba contamination from the managed runtime environment.
- verification: `node --test tests/launcher_uv.test.cjs`

- local_commit: `4c82f68`
- upstream_bundle:
  - `9ef9858a99fe2c01d66eb3aa3c0ea5ac412cbfd9`
  - `38b74d83f4097f1f0163a2470c612400f3b90515`
- kind: `runtime_bugfix`
- reason: provider-backed Codex profiles now surface stable metadata, override conflicting top-level probe config, force `model: inherit` when a profile already owns model selection, and strip conflicting OpenAI auth env for `requires_openai_auth = false`.
- verification:
  - `uv run pytest -q tests/test_codex_cli_compat.py tests/test_config_testing.py tests/test_codex_runner.py`
  - `uv run pytest -q tests/test_codex_cli_compat.py tests/test_config_testing.py tests/test_codex_runner.py -k "codex or profile or provider or inherit or minimax"`

- local_commit: `a027ef3`
- upstream_commit: `1e922bab92f338fba240bfc7c72fd28a57820a26`
- kind: `runtime_bugfix`
- reason: run-scoped Codex homes now materialize global `config/auth/skills/agents/prompts`, overlay quest-local `skills/prompts`, and prune stale runtime-home payloads while preserving the fork's `quest_root/.ds/codex_homes/<run_id>` contract.
- verification:
  - `uv run pytest -q tests/test_codex_cli_compat.py tests/test_codex_runner.py tests/test_runtime_storage.py`
  - `uv run pytest -q tests/test_codex_runner.py -k "project_home or run_scoped or codex_home"`

- local_commit: `9043bb3`
- upstream_commit: `c8a8178c4d695ffe9f16a9ff48baadea2df2cc6a`
- kind: `runtime_bugfix`
- reason: chat-wire provider sessions now inject a prompt-level tool-call serialization guard so Codex emits one MCP call per assistant turn instead of bundling multiple tool calls into a single reply.
- verification: `uv run pytest -q tests/test_codex_runner.py -k "chat_wire or single_tool_guard or provider or profile"`

- local_commit: `14bc695`
- upstream_commit: `042b1bad0a4e4cd2fed5d02fb6e288a5e47d6e5e`
- kind: `runtime_bugfix`
- reason: Codex runner subprocess launch now reuses the shared process-control helper, keeping Windows console hiding and process-group behavior aligned with the rest of the runtime.
- verification: `uv run pytest -q tests/test_codex_runner.py tests/test_windows_support.py -k "windows or popen or process_session"`

- local_commit: `f15ccdb`
- upstream_bundle:
  - `07fa212b50aae8055bf12e58768d619b35386b62`
  - `17340bd112d1688f2fa403f545d4f3b874e27e3b`
- kind: `launcher_bugfix`
- reason: launcher management commands now emit richer status diagnostics and can rediscover a same-directory `./DeepScientist` managed home for `--status`, `--stop`, and `--restart`, while source-checkout wrapper repair can be forced for explicit non-default homes.
- verification:
  - `node --test tests/launcher_uv.test.cjs`
  - `uv run pytest -q tests/test_launcher_status.py`

- local_commit: `fcba71f`
- upstream_commit: `ea1329ddacf9c7a919f71c40bdb1ca1438943656`
- kind: `runtime_bugfix`
- reason: older corrupted event history lines no longer break daemon event pagination, so the stable `/api/quests/{quest_id}/events` surface keeps returning usable cursors and history slices.
- verification: `uv run pytest -q tests/test_acp_api.py`

- local_commit: `838f87e`
- upstream_commit: `54a460070d0cdf3efb82a4d8f7368ee0488d707d`
- kind: `runtime_bugfix`
- reason: runtime recovery now records clearer retry classification and doctor diagnostics, which strengthens MAS-facing stalled-run repair without widening the runtime contract.
- verification:
  - `uv run pytest -q tests/test_doctor.py`
  - `uv run pytest -q tests/test_daemon_api.py`

- local_commit: `a255de4`
- upstream_bundle:
  - `4c3fbbcbcadb670c26b86453632a6bd4b1cab59a`
  - `f417d82be02a4f6dc53d58b230fdcad20d3476a1`
  - `1b18d2e0ff54bba61ef7f317313983cb47e74725`
- kind: `runtime_bugfix`
- reason: daemon-served assets and hidden-window git subprocesses now behave consistently on Windows, reducing cross-platform runtime friction while preserving the existing API and layout boundaries.
- verification:
  - `uv run pytest -q tests/test_daemon_api.py -k ui_asset_prefers_explicit_javascript_mime_over_platform_guess`
  - `uv run pytest -q tests/test_shared.py tests/test_windows_support.py`

### Round 2 follow-up partial intake

- local_commit: `223f086`
- upstream_partial: `1865fa5e608e5ccc0f9b92ba72fc770791538847`
- kind: `runtime_bugfix`
- reason: current metrics timelines now prefer human-readable baseline variant labels, and idea interaction messages keep full connector-facing text instead of truncating the substantive tail inline.
- verification:
  - `uv run pytest -q tests/test_metrics_overview_surface.py`
  - `uv run pytest -q tests/test_memory_and_artifact.py -k idea_interaction_message`
  - `scripts/verify.sh`

### Round 3 UI and TUI micro-intake

- local_commit: `945206f`
- upstream_commit: `3037b537c5ff7ebff10fc89d315aa95614513798`
- kind: `ui_bugfix`
- reason: workspace stage details, lab text summaries, and persisted custom tabs now normalize circular objects through a dedicated front-end helper instead of relying on raw `JSON.stringify(...)`.
- verification:
  - `cd src/ui && npm run build`
  - `uv run pytest -q tests/test_ui_source_contracts.py`

- local_commit: `1a8139c`
- upstream_commit: `52472325aeeda8e17ff23b7155073aa9724ba246`
- kind: `tui_bugfix`
- reason: the TUI quest browser now lets `QuestScreen` own arrow navigation while `AppContainer` limits its global browse shortcuts to config browse mode, so one keypress advances one item.
- verification:
  - `npm --prefix src/tui run build`
  - `uv run pytest -q tests/test_api_contract_surface.py -k tui_client_and_git_canvas_follow_same_protocol_contract`

### Round 4 latest-update learning intake

- local_commit: `df714e6b3831e044f9f56100412089d1c74a1f7f`
- upstream_bundle:
  - `87c1e93` `fix: improve quest file search path matching`
  - `b3823a0` `start-setup: recover form patch fallback across runners`
  - `4a8c86a` `feat: add artifact baseline overwrite and paper coverage flows`
  - `069b9cc` `feat: expose artifact planning tools through MCP`
  - `13d3fc7` `test: align paper checkpoint connector milestone`
  - `990ca6e` `bash_exec: bound await waits without killing sessions`
- kind: `runtime_intake`
- reason: current upstream added several bounded runtime lessons that strengthen this fork without importing broad provider or product-shell churn: path-aware workspace search, durable start-setup planning state, manuscript-vs-submission coverage truth, ready duplicate paper evidence selection, and bounded long-run await discipline.
- verification:
  - `uv run pytest -q tests/test_init_and_quest.py::test_search_files_matches_paths_and_normalizes_simple_globs tests/test_mcp_servers.py::test_start_setup_profile_artifact_server_exposes_prepare_form_only tests/test_mcp_servers.py::test_artifact_mcp_server_tools_cover_core_flows tests/test_memory_and_artifact.py::test_validate_manuscript_coverage_blocks_short_memo_as_full_paper tests/test_memory_and_artifact.py::test_get_paper_contract_health_prefers_ready_duplicate_ledger_item tests/test_prompt_builder.py::test_prompt_builder_includes_paper_contract_health_block tests/test_skill_contracts.py::test_system_prompt_strengthens_bash_exec_only_terminal_contract tests/test_skill_contracts.py::test_experiment_and_analysis_skills_require_smoke_then_detach_tail_monitoring`
  - `git diff --check`

## Lock Policy

- mode: `regenerate_in_fork`
- source_repo_was_dirty: `true`
- source_dirty_paths:
  - `uv.lock`
- regenerated_after_commit: `d4994dba3ae1720a60daa7c80f5043f3722f32d8`

## Intake Policy

Future upstream absorption must follow the controlled intake procedure documented in [`docs/upstream_intake.md`](./upstream_intake.md).
