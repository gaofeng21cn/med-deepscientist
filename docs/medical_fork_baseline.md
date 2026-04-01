# med-deepscientist Freeze Baseline

- public_project_name: `med-deepscientist`
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

`med-deepscientist` is a controlled fork used as the stable runtime layer under `MedAutoScience`.
It exists to preserve long-running quest execution, daemon compatibility, and auditable runtime behavior while upstream `DeepScientist` continues to evolve on its own cadence.

Remote semantics are explicit:

- `origin` is the canonical `med-deepscientist` GitHub repository
- `upstream` is the upstream `DeepScientist` repository used for intake comparison
- controlled-fork upgrade checks compare against `upstream/main`, not against the fork's own `origin/main`

## Applied Patchset

### Phase 1 runtime bugfix

- commit: `d4994dba3ae1720a60daa7c80f5043f3722f32d8`
- kind: `runtime_bugfix`
- reason: `document_asset` must resolve path documents from the active worktree so Web App previews for PNG / SVG / PDF remain correct.
- verification: `PYTHONPATH=src pytest -q tests/test_daemon_api.py -k 'document_asset_resolves_path_documents_from_active_worktree'`

## Lock Policy

- mode: `regenerate_in_fork`
- source_repo_was_dirty: `true`
- source_dirty_paths:
  - `uv.lock`
- regenerated_after_commit: `d4994dba3ae1720a60daa7c80f5043f3722f32d8`

## Intake Policy

Future upstream absorption must follow the controlled intake procedure documented in [`docs/upstream_intake.md`](./upstream_intake.md).
