# Medical Fork Baseline

Controlled Phase 1 fork of DeepScientist for medical research runs. All work targets the snapshot locked at `a7853fda3432d37f6dee91fa6e66330f564bd8be` and cherry-picks the vetted patch `d4994dba3ae1720a60daa7c80f5043f3722f32d8`.

## Verification Checklist

1. `uv lock` must be reconstructed inside this repository so `uv.lock` reflects the controlled requirements.
2. Run `PYTHONPATH=src pytest -q tests/test_daemon_api.py -k 'document_asset_resolves_path_documents_from_active_worktree'` to confirm daemon API behavior remains aligned with the baseline.
3. Any additional changes must be tracked via `MEDICAL_FORK_MANIFEST.json` and audited before inclusion.
