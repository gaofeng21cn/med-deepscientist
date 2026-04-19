# Upstream Intake Audit 2026-04-19

This audit records the second controlled upstream intake round for MedDeepScientist against `upstream/main`.

## Snapshot

- audit_date: `2026-04-19`
- target_repo: `MedDeepScientist` (repository `med-deepscientist`)
- comparison_ref: `upstream/main`
- merge_base: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- rev_list_main_vs_upstream: `ahead=97, behind=105`
- audit_status: `classified_and_executed`
- execution_status: `round2_absorbed_on_main_with_followup`

## Evidence

The audit was based on these fresh git checks:

```bash
git fetch upstream main --prune
git rev-list --left-right --count main...upstream/main
git merge-base main upstream/main
git log --reverse --oneline main..upstream/main
git cherry -v main upstream/main
git log --oneline main..HEAD
```

At the start of this round, `git cherry -v main upstream/main` already showed `d4994db` and `bf97bfb` as absorbed equivalents on `main`, while the runtime and launcher fixes targeted below were still pending.

## Selection Rule For This Round

Round 2 focused on upstream changes that satisfy all of these:

- improve daemon correctness or long-running quest recovery
- harden the `MedAutoScience -> MedDeepScientist` runtime seam
- preserve the fork's quest layout, daemon API shape, and run-scoped runtime storage
- keep launcher changes bounded to managed-home diagnostics and runtime bootstrap correctness

This round intentionally left out prompt wording, stage-skill wording, README churn, UI/product features, connector-specific fixes, and optional companion skills.

## Selected Intake Bundle

### Batch A: daemon and MCP runtime fixes

1. upstream commit `01b8901d0066cce3a598e0185d861b88c6f571b9` `fix: normalize list-wrapped bash_exec commands`
   - decision: `absorb`
   - local commit: `ec845f3`
   - rationale: newer FastMCP payloads can hand `command` in list form, and the fork needs to accept that shape without widening the MCP contract.

2. upstream bundle
   - `5364b6212e276bb4cc2e6a0d9353ebc5f6cfbccb` `Recover stalled running turns when new user messages arrive`
   - `1a5333c2e629471ff1100b113ac67f28bc7a3288` `fix stalled turn recovery state handling`
   - `be386ae912b9d496edf6d46982ff280083ab6dbf` `finish stalled turn recovery follow-up`
   - `e41f6a798298f8854607dbe9a885bd1b5b8d074b` `respect stop and pause during recovery watch`
   - `af8d0e263bc7fcd0721318e1d4b3cdb26a1b6ce3` `fix concurrent stalled-turn recovery`
   - decision: `absorb_adapted`
   - local commit: `b928098`
   - rationale: the fork needs stalled-turn recovery for queued user messages, but the absorbed implementation must also emit runtime reconciliation events and trigger runtime storage maintenance.

### Batch B: launcher runtime bootstrap hardening

1. upstream bundle
   - `4f0975625c182f3b784c61921776f6c76d375951` `Sanitize conda env during uv bootstrap`
   - `a149a22b890d9bd5d487f9bb764aad6cabc5a79f` `fix: resolve 'npmBinary is not defined' error during auto-update`
   - decision: `absorb`
   - local commit: `6e60e3f`
   - rationale: both changes directly improve managed runtime bootstrap and self-update reliability.

### Batch C: Codex provider and runtime home compatibility

1. upstream bundle
   - `9ef9858a99fe2c01d66eb3aa3c0ea5ac412cbfd9` `fix: repair MiniMax Codex compatibility`
   - `38b74d83f4097f1f0163a2470c612400f3b90515` `fix MiniMax profile shadowing in Codex probe homes`
   - decision: `absorb_adapted`
   - local commit: `4c82f68`
   - rationale: provider-backed profile metadata, `model: inherit`, and `requires_openai_auth = false` env cleanup all improve Codex runtime stability for MAS-facing provider profiles.

2. upstream commit `1e922bab92f338fba240bfc7c72fd28a57820a26` `Fix Codex runtime home inheritance semantics`
   - decision: `absorb_adapted`
   - local commit: `a027ef3`
   - rationale: the fork keeps its own `quest_root/.ds/codex_homes/<run_id>` invariant, so this intake absorbs directory sync and stale cleanup semantics while preserving the run-scoped target layout.

3. upstream commit `c8a8178c4d695ffe9f16a9ff48baadea2df2cc6a` `Fix MiniMax chat-wire MCP tool batching`
   - decision: `absorb`
   - local commit: `9043bb3`
   - rationale: chat-wire provider sessions need a prompt-level MCP serialization guard; this is high value and low surface area.

4. upstream commit `042b1bad0a4e4cd2fed5d02fb6e288a5e47d6e5e` `Hide Windows codex runner console windows`
   - decision: `absorb`
   - local commit: `14bc695`
   - rationale: the repository already owns a shared process-control helper, so folding runner launch into that helper reduces Windows-specific drift.

### Batch D: launcher management diagnostics

1. upstream bundle
   - `07fa212b50aae8055bf12e58768d619b35386b62` `Fix launcher wrapper home resolution`
   - `17340bd112d1688f2fa403f545d4f3b874e27e3b` `Fix launcher stop/status home detection`
   - decision: `absorb_partial`
   - local commit: `f15ccdb`
   - rationale: status payload diagnostics, cwd-local managed-home discovery, and forceable wrapper repair help real launcher operations; install-index fallback was intentionally left out because this fork does not currently maintain install-index infrastructure.

### Batch E: runtime follow-up fixes

1. upstream commit `ea1329ddacf9c7a919f71c40bdb1ca1438943656` `Fix corrupted older event history pagination`
   - decision: `absorb`
   - intake branch commit: `fde32bd`
   - merged `main` commit: `fcba71f`
   - rationale: `GET /api/quests/{quest_id}/events` is part of the stable daemon/runtime surface, so cursor semantics must remain correct even when older history contains corrupted JSONL lines.

2. upstream commit `54a460070d0cdf3efb82a4d8f7368ee0488d707d` `Improve runtime recovery and doctor diagnosis`
   - decision: `absorb_adapted`
   - intake branch commit: `06e4d24`
   - merged `main` commit: `838f87e`
   - local follow-up commit: `a32ef0b`
   - rationale: persisted retry recovery, deterministic non-retryable failure diagnosis, and doctor-side `problem / why / fix` reporting all strengthen MAS-facing runtime recovery without widening product surface.

## Explicitly Deferred

The following upstream groups remain outside this round by design:

- prompt and stage-skill wording bundles such as `5a3c1c6`, `f2c85bc`, `76c135c`, `6d30f47`, `4b63ddc`, `01202f2`, and `56d3cd4`
- UI, TUI, and product-surface features such as `77e97d9`, `7c9c03f`, `27211b3`, `5247232`, `3fbc9be`, `b707d94`, and `4c3fbbc`
- workspace-mode continuation fixes `d58a655` and `d9d4bd6`, because this fork already uses `workspace_mode` for durable workspace/layout semantics while the stable control field remains `startup_contract.decision_policy`
- connector-specific fixes such as `c3abc96` and `efe6c57`
- docs / README / release / badge churn
- optional companion skill `1c151a8` `skills: add paper-plot companion skill`

## Execution Result

This round used a dedicated intake worktree and produced the following local intake commits:

1. `ec845f3` `Normalize list-wrapped bash_exec commands`
2. `b928098` `Recover stalled live turns before queued user messages stall`
3. `6e60e3f` `Harden launcher self-update and uv bootstrap env`
4. `4c82f68` `Harden Codex provider profile compatibility`
5. `a027ef3` `Materialize run-scoped Codex homes from provider overlays`
6. `9043bb3` `Serialize chat-wire Codex tool calls`
7. `14bc695` `Hide Codex runner windows through process control helper`
8. `f15ccdb` `Improve launcher management home diagnostics`
9. `fcba71f` `Fix corrupted older event history pagination`
10. `838f87e` `feat: improve runtime recovery diagnosis`
11. `a32ef0b` `test: stabilize retry recovery timing coverage`

Merge-back verification on the same intake branch also exposed 5 pre-existing `main` failures in `tests/test_init_and_quest.py`. Those were repaired locally before merge-back by:

- aligning stale test expectations with the current fork defaults for `codex.model = "inherit"` and paper-line bundle gating
- keeping `QuestService` blocker payloads stable while restoring display-normalized blocker surfaces in `ArtifactService`
- ensuring `completion_blocking_reasons` retains managed publication gate blockers even when local bundle blockers are also present

## Verification

The round exercised fresh focused verification after each absorbed batch:

```bash
uv run pytest -q tests/test_mcp_servers.py -k "bash_exec_mcp_server_normalizes_list_wrapped_commands or bash_exec_mcp_server_supports_detach_read_list_and_kill"
uv run pytest -q tests/test_daemon_api.py
node --test tests/launcher_uv.test.cjs
uv run pytest -q tests/test_codex_cli_compat.py tests/test_config_testing.py tests/test_codex_runner.py
uv run pytest -q tests/test_codex_cli_compat.py tests/test_codex_runner.py tests/test_runtime_storage.py
uv run pytest -q tests/test_codex_runner.py tests/test_windows_support.py -k "windows or popen or process_session"
uv run pytest -q tests/test_launcher_status.py
uv run pytest -q tests/test_init_and_quest.py
uv run pytest -q tests/test_acp_api.py
uv run pytest -q tests/test_doctor.py
uv run pytest -q tests/test_daemon_api.py
uv run pytest -q
scripts/verify.sh
```

Key outcomes:

- `tests/test_daemon_api.py`: `141 passed`
- `tests/test_codex_cli_compat.py tests/test_config_testing.py tests/test_codex_runner.py`: `65 passed`
- `tests/test_codex_cli_compat.py tests/test_codex_runner.py tests/test_runtime_storage.py`: `39 passed`
- `tests/test_codex_runner.py tests/test_windows_support.py -k "windows or popen or process_session"`: `7 passed`
- `tests/test_launcher_status.py`: `1 passed`
- `tests/launcher_uv.test.cjs`: `23 tests, 23 pass`
- `tests/test_init_and_quest.py`: `35 passed`
- `tests/test_acp_api.py`: `9 passed`
- `tests/test_doctor.py`: `5 passed`
- `tests/test_daemon_api.py`: `144 passed in 224.75s (0:03:44)`
- full `uv run pytest -q`: `747 passed, 5 warnings in 1177.68s (0:19:37)`
- `scripts/verify.sh`: `55 passed`

## Next Action

Round 2 follow-up is now absorbed on `main`. Remaining future review items are:

- keep `d58a655` + `d9d4bd6` in `defer` until they are rewritten around the fork's stable decision-policy contract
- keep `4c3fbbc` as a separate Windows daemon/UI supporting-fix lane
- keep optional companion skill `1c151a8` outside the runtime seam unless paper-plotting becomes a concrete MAS runtime need
