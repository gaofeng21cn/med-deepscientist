# MedicalDeepScientist Freeze Baseline

- engine_family: `MedicalDeepScientist`
- freeze_mode: `thin_fork`
- upstream_repo_path: `/Users/gaofeng/workspace/DeepScientist`
- upstream_base_commit: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- phase: `phase1_local_freeze`
- package_rename_applied: `false`
- daemon_api_shape_preserved: `true`
- quest_layout_preserved: `true`
- worktree_layout_preserved: `true`

This repository is a controlled local fork used to stabilize runtime truth before protocol convergence work begins in `MedAutoScience`.

## Applied Phase 1 Patch

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
