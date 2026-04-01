# Upstream Intake Audit 2026-04-01

This audit records the first controlled intake split for MedDeepScientist against upstream `DeepScientist`.

## Snapshot

- audit_date: `2026-04-01`
- target_repo: `MedDeepScientist` (repository `med-deepscientist`)
- comparison_ref: `upstream/main`
- merge_base: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- rev_list_main_vs_upstream: `ahead=6, behind=7`
- audit_status: `classified`
- execution_status: `intake_worktree_created_blocked_by_preexisting_baseline_failure`

## Evidence

The audit was based on these git checks:

```bash
git fetch upstream main --prune
git rev-list --left-right --count main...upstream/main
git merge-base main upstream/main
git log --reverse --oneline main..upstream/main
git cherry -v main upstream/main
```

`git cherry -v` shows that `d4994db` is already absorbed by an equivalent local patch, while the other non-merge commits remain unabsorbed.

## Classification

### Batch A: round-1 absorb

Only one commit fits the current round-1 goal of improving runtime stability without widening the compatibility surface unnecessarily.

1. `bf97bfbf3fa4119924b10e2ff2c9edabece0b402` `fix: stabilize stage routing for bootstrap quests`
   - decision: `absorb`
   - type: `runtime_bugfix`
   - rationale: touches daemon stage routing and prompt builder consistency, adds direct regression tests, and fits the runtime-stability goal of the fork.

### Batch B: do not absorb in round 1

These commits are either outside the runtime-stability target, already absorbed, or not valid intake units.

1. `1865fa5e608e5ccc0f9b92ba72fc770791538847` `feat: split baseline compare and interaction previews`
   - decision: `defer_feature`
   - type: `runtime_feature`
   - rationale: spans runtime, API, UI, prompt, skill, and artifact surfaces. It is not a narrow compatibility fix, so absorbing it now would widen the fork's maintenance surface before the stable runtime line is fully settled.
2. `4bff80151d9fa067672f47370f1fdd04fd54c91a` `docs: add external controller guide`
   - decision: `reject_docs`
   - type: `docs`
   - rationale: documentation-only and oriented to the upstream product surface, while this fork is already maintaining its own public documentation.
3. `3f3491759c1c931fbce3c3c08f0f60120ff5c127` `docs: add controller examples and renumber guide`
   - decision: `reject_docs`
   - type: `docs`
   - rationale: follow-up documentation reshaping for the upstream surface, not a runtime-stability patch for this fork.

### Batch C: do not intake

These commits should not be imported as new work.

1. `d4994dba3ae1720a60daa7c80f5043f3722f32d8` `Fix worktree document asset resolution`
   - decision: `reject_duplicate`
   - type: `runtime_bugfix`
   - rationale: already present locally as equivalent commit `ea80c3c`.
2. `634b1fd` `Merge pull request #11 from gaofeng21cn/codex/pr2-external-controller-docs`
   - decision: `reject_merge_wrapper`
   - type: `merge_commit`
   - rationale: merge wrapper for the documentation PR, not an intake unit by itself.
3. `be424ed` `Merge pull request #13 from gaofeng21cn/codex/fix-document-asset-worktree`
   - decision: `reject_merge_wrapper`
   - type: `merge_commit`
   - rationale: merge wrapper for the already-absorbed document-asset fix, not an intake unit by itself.

## Next Action

Create a dedicated intake worktree and execute `bf97bfb` with fork regression plus MedAutoScience compatibility regression. Revisit `1865fa5` only as a separate feature-evaluation intake after the runtime-stability line is proven clean.

## Current Blocker

An intake worktree has already been created at:

```text
/Users/gaofeng/workspace/med-deepscientist/.worktree/intake-2026-04-01-bootstrap-routing
```

No upstream commit has been cherry-picked yet. Baseline verification in that clean worktree exposed a pre-existing failure before intake started:

```bash
rtk uv run pytest tests/test_daemon_api.py tests/test_prompt_builder.py -x -vv
```

Observed blocker:

- failing test: `tests/test_daemon_api.py::test_bash_exec_handlers_expose_sessions_logs_and_stop`
- reproduced on intake worktree before any cherry-pick
- reproduced again on repository `main`, confirming that this is a baseline issue rather than an intake regression
