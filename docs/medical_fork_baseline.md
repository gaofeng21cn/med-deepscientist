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

## Lock Policy

- mode: `regenerate_in_fork`
- source_repo_was_dirty: `true`
- source_dirty_paths:
  - `uv.lock`
- regenerated_after_commit: `d4994dba3ae1720a60daa7c80f5043f3722f32d8`

## Intake Policy

Future upstream absorption must follow the controlled intake procedure documented in [`docs/upstream_intake.md`](./upstream_intake.md).
