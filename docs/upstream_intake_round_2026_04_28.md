# Upstream Intake Audit 2026-04-28

这份审计记录了 `MedDeepScientist` 在 2026-04-28 对 `upstream/main` 的最新一轮 learning-and-landing intake。

## 快照

- audit_date: `2026-04-28`
- target_repo: `MedDeepScientist` (`med-deepscientist`)
- comparison_ref: `upstream/main`
- comparison_head: `d22165e` `docs: explain workspace explorer file visibility`
- fork_head_before_round: `0e09065`
- merge_base: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- rev_list_before_round: `ahead=216, behind=177`
- execution_status: `focused_runtime_slice_absorbed`
- local_intake_commit: `df714e6b3831e044f9f56100412089d1c74a1f7f`

## Fresh Audit Commands

```bash
git fetch upstream --prune
git rev-list --left-right --count main...upstream/main
git merge-base main upstream/main
git log --reverse --oneline bfc8675..upstream/main
git show --stat --oneline upstream/main~18..upstream/main
```

## Decision Matrix

### A. Adopted Code Slices

1. upstream `87c1e93` `fix: improve quest file search path matching`
   - decision: `adopt_code_slice`
   - owner_surface: `MDS quest/workspace explorer`
   - learned_capability: workspace explorer search must find path matches, not only text-body matches; simple user glob forms such as `*analysis_plan*` should map to the path search users expect.
   - local landing: `QuestService.search_files(...)` now normalizes simple wrapping globs and emits path-level matches with `line_number=0`.

2. upstream `b3823a0` / `abc4baf` start-setup planning chain
   - decision: `adopt_code_slice_adapted`
   - owner_surface: `MDS start_setup artifact/MCP bridge`
   - learned_capability: setup agents should be able to return both form fields and planning/session assessment state as one durable patch, because the UI effect alone is not enough for resumable setup.
   - local landing: `artifact.prepare_start_setup_form(...)` now accepts sanitized `session_patch`, persists it into `quest.yaml -> startup_contract.start_setup_session`, and keeps nested runner payloads compatible.

3. upstream `4a8c86a` / `069b9cc` paper coverage and planning surfaces
   - decision: `adopt_code_slice_adapted`
   - owner_surface: `MDS paper artifact oracle`
   - learned_capability: a short memo, review package, and submission-ready manuscript must be separate runtime states; agents need a callable coverage gate before making full-manuscript or submission claims.
   - local landing: added `artifact.validate_manuscript_coverage(...)`, MCP exposure, Codex built-in approval, prompt wiring, and write/review/finalize skill discipline.

4. upstream `13d3fc7` paper checkpoint connector milestone alignment
   - decision: `adopt_code_slice_adapted`
   - owner_surface: `MDS paper contract health`
   - learned_capability: duplicate ledger rows for the same required item should prefer a ready main-text support row over a stale pending row.
   - local landing: `get_paper_contract_health(...)` now groups duplicate evidence ledger items and selects ready/main-text evidence first.

5. upstream `990ca6e` bounded `bash_exec` awaits
   - decision: `adopt_template`
   - owner_surface: `MDS prompt/skill runtime discipline`
   - learned_capability: waiting on an already-running managed session should use bounded `wait_timeout_seconds`, then inspect logs and progress before another wait, instead of treating timeout as failure or launching extra sleeps.
   - local landing: system prompt plus experiment / analysis-campaign skill instructions now use `bash_exec(mode='await', id=..., wait_timeout_seconds=1800)` and explain the next read-and-judge step.

## Already Covered By Existing Local Main

The fresh audit also confirmed several recent upstream capabilities were already represented on this fork before this worktree started:

- upstream `710792e` baseline overwrite refresh: local `7910cd9` had already landed `artifact.overwrite_baseline(...)`.
- upstream `ff7d2f5` retry-backoff user-message priority: local `e5032f2` had already landed the preempting retry/backoff behavior.
- upstream `2ecf048` runner / prompt / admin service runtime updates: local runner diagnostics, provider handling, system visibility, and runtime failure taxonomy commits already covered the fork-relevant parts.

## Deferred Or Rejected

### Provider runner expansion

- upstream candidates: `a1fe3e6`, `1f7c1a2`, `96a3b0d`, `2415c5d`, `e539e2e`, `00e6860`
- decision: `reject_for_now`
- rationale: Claude / Kimi / provider runner expansion is not a current `MedAutoScience -> MedDeepScientist` compatibility need. The fork keeps `claude` and `opencode` as reserved experimental ids and lets Codex profile compatibility carry provider diversity.

### Broad UI shell changes

- upstream candidates: `3b00c1f`, `4b8cc85`, `9566b7c`, `4c4022e`, `e68ce05`, `54ef5f0`, `7bcfdcf`, `b63a179`, `5d910d4`, `abc4baf`, `b0430db`, `23ecfb9`, `d22165e`
- decision: `watch_only`
- rationale: these changes are mostly product shell, Settings, chat, lab canvas, and workspace UI behavior. The directly useful backend/search/start-setup semantics were absorbed without pulling the UI product surface wholesale.

### Full stage-skill restructuring

- upstream candidates: `7aa333f`, `3ce3220`, `caf6b15`, `335d4ba`, `5f84848`
- decision: `adopt_template_partial`
- rationale: the useful method lesson is stronger stage operational packets, especially analysis/write/finalize discipline. This round only absorbed the bounded-await and manuscript-coverage readiness rules that directly affect current fork runtime behavior. Wider skill restructuring remains a future owner-boundary review item.

### Install / DeepXiv hardening

- upstream candidate: `0cc623e`
- decision: `watch_only`
- rationale: install-copy and DeepXiv config hardening is useful upstream hygiene, but it does not change the current MAS runtime compatibility surface.

## Verification

Focused MDS tests:

```bash
uv run pytest -q \
  tests/test_init_and_quest.py::test_search_files_matches_paths_and_normalizes_simple_globs \
  tests/test_mcp_servers.py::test_start_setup_profile_artifact_server_exposes_prepare_form_only \
  tests/test_mcp_servers.py::test_artifact_mcp_server_tools_cover_core_flows \
  tests/test_memory_and_artifact.py::test_validate_manuscript_coverage_blocks_short_memo_as_full_paper \
  tests/test_memory_and_artifact.py::test_get_paper_contract_health_prefers_ready_duplicate_ledger_item \
  tests/test_prompt_builder.py::test_prompt_builder_includes_paper_contract_health_block \
  tests/test_skill_contracts.py::test_system_prompt_strengthens_bash_exec_only_terminal_contract \
  tests/test_skill_contracts.py::test_experiment_and_analysis_skills_require_smoke_then_detach_tail_monitoring
```

Result:

- `8 passed in 17.05s`

Additional pre-commit check:

```bash
git diff --check
```

Result:

- clean

## Outcome

This round did not bulk-sync upstream. It absorbed the bounded runtime/backend slices that strengthen:

- workspace file/path discoverability
- guided setup session durability
- manuscript-vs-submission readiness truth
- duplicate paper evidence ledger handling
- long-run wait discipline

Remaining provider and UI product-surface changes stay outside the controlled fork mainline until they map to a clear MAS/MDS owner surface and verification target.
