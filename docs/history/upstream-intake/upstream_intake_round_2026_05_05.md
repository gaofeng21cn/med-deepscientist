# Upstream Intake Audit 2026-05-05

这份审计记录了 `MedDeepScientist` 在 2026-05-05 对 `upstream/main` 的 latest-update learning round，以及 fork PR head branch 清理结果。

## 快照

- audit_date: `2026-05-05`
- target_repo: `MedDeepScientist` (`med-deepscientist`)
- comparison_ref: `upstream/main`
- comparison_head: `bd0b92b` `Polish BenchStore tutorial flow`
- previous_intake_head: `1f042ef` `docs: expand provider setup guidance`
- local_main_at_audit: `e655e2c` `Retire docs prose contract tests`
- origin_main_at_audit: `e655e2c` `Retire docs prose contract tests`
- merge_base: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- rev_list_before_round: `ahead=278, behind=241`
- execution_status: `one_mds_runtime_slice_plus_pr_branch_cleanup`
- mds_code_landing: `f1f3d0f` `Mirror refreshed summaries to quest root`

## Fresh Audit Commands

```bash
git fetch --all --prune
git rev-list --left-right --count main...upstream/main
git log --reverse --oneline 1f042ef..upstream/main
git diff --name-status 1f042ef..upstream/main
gh pr list --repo ResearAI/DeepScientist --author gaofeng21cn --state all --limit 30
gh pr list --repo ResearAI/DeepScientist --state open --limit 50
git ls-remote --heads pr-fork 'codex/*'
```

Observed state:

- `upstream/main` refreshed to `bd0b92b`.
- `gh pr list --author gaofeng21cn --state open` returned `[]`.
- Our upstream PRs #65, #66, #67, #71, #72, #73, and #74 are merged.
- Older PRs #11 and #13 are merged; #10 is closed and obsolete after the later stop-loss guidance work.
- The fork remote `pr-fork` had stale `codex/*` head branches for those PRs before cleanup; after deletion and prune, `git ls-remote --heads pr-fork 'codex/*'` returned no heads.

## Decision Matrix

### A. Adopted In MDS Runtime

1. upstream `9f5066b` `fix(artifact): refresh_summary mirrors SUMMARY.md to quest_root`

- decision: `adopt_mds_runtime_slice`
- owner_surface: `MDS artifact service / canonical quest summary`
- local_landing: `f1f3d0f` `Mirror refreshed summaries to quest root`
- learned_capability: explicit `artifact.refresh_summary(...)` should update the active workspace summary and the canonical `quest_root/SUMMARY.md`, so external supervisors and MAS-side readers do not have to infer current quest state from a branch worktree.
- rationale: this is a bounded runtime truth-surface fix. It preserves daemon API shape and quest/worktree layout, adds a directly verifiable return path, and avoids importing upstream's broader product or UI changes.
- verification: `PYTHONPATH=src uv run pytest -q tests/test_memory_and_artifact.py -k 'refresh_summary'` -> `2 passed, 164 deselected`.

### B. Already Covered Or Stronger Locally

1. upstream merged PRs #65, #66, #67
   - decision: `already_covered`
   - owner_surface: `MDS runner diagnostics / evidence packets / runtime storage`
   - rationale: these were already classified in the 2026-04-30 intake round. Current MDS main already carries the corresponding AI-first telemetry, evidence packet, log hygiene, and runner-diagnostics lessons.

2. upstream merged PRs #71 and #72
   - decision: `already_covered`
   - owner_surface: `MDS read-cache telemetry / runtime storage maintenance`
   - rationale: these originated from our upstream PRs and are already represented by current MDS runtime storage and telemetry surfaces. No new fork code slice was needed in this round.

3. upstream merged PRs #73 and #74
   - decision: `already_covered_or_mas_owned`
   - owner_surface: `MDS paper artifact deltas / publishability stop-loss guidance`
   - rationale: paper artifact delta behavior is already present in the fork's paper artifact flows. Publishability stop-loss remains a MAS/MDS policy lesson, not a reason to broaden MDS product ownership.

### C. Watch Only

1. upstream `03748cf`, `d390f1d`, `f7b707a`, `5a4107a`, `6fb599f`, `721a01c`, `7415015`
   - decision: `watch_only`
   - rationale: cross-quest recall prose, prescriptive limitations guidance, framework-quirk scaffolding, prompt summary reminders, exploration-depth stopping discipline, and autonomous launch policy are useful research-agent ideas. They are prompt/skill/product orchestration changes, so they should become MAS/MDS owner truth only through a bounded contract or testable runtime seam.

2. upstream open PR #82 `[Bugfix] Auto-refresh quest_root SUMMARY.md on every artifact.record`
   - decision: `watch_only`
   - rationale: the intent is aligned with canonical summary freshness, but it changes every artifact record into an implicit summary update and wraps refresh failure as non-blocking side effect. This round absorbed only the explicit `refresh_summary` mirror, which is narrower and directly testable.

### D. Rejected / Deferred Product Surface

1. upstream `3f3e413`, `1ab22b8`, merge `d25d457`
   - decision: `defer_connector_runtime`
   - rationale: Weixin long-poll timeout hardening is a real upstream connector bugfix. Current MDS does not treat Weixin as MAS-facing default runtime contract, so this stays watch-only unless a local connector runtime blocker appears.

2. upstream `d90a8b3`, `040dfee`, merge `3652d8d`
   - decision: `defer_installer_surface`
   - rationale: deterministic `npm ci` install and runtime Python env invalidation are useful operator changes, but they are installer/release surfaces rather than the current MAS/MDS runtime compatibility contract.

3. upstream `d51cdd0`, `b5846e2`, merge `a402e4f`
   - decision: `not_applicable_to_current_fork`
   - rationale: current MDS does not expose the upstream `sharedmemory::` document-id surface, so direct absorption would add a dormant contract rather than repair an active one.

4. upstream `d6bc5fd`, `695f504`, `3be0dc8`, `251bb44`, `3508099`, `862bc0c`, `a1eb9dd`, `bd0b92b`
   - decision: `reject_for_current_mds_mainline`
   - rationale: BenchStore/AISB catalog, tutorial, and display updates are upstream product breadth. They do not strengthen the current `MedAutoScience -> MedDeepScientist` compatibility contract.

5. upstream `91492bb`, `dbddafa`, `3c47491`, `e6f4ba5`, `1a7a236`
   - decision: `reject_for_current_mds_mainline`
   - rationale: admin issue draft alignment, mobile/debug UI, TUI utility panels, and Nature companion skills are product/user-surface expansion. They are not default MAS runtime truth.

6. upstream open PR #68 `Add MseeP.ai badge`
   - decision: `reject_product_badge`
   - rationale: badge-only README change has no compatibility or runtime value for the controlled fork.

## PR Cleanup

No open `gaofeng21cn` PRs remained on `ResearAI/DeepScientist`.

The following stale fork branches were deleted from `pr-fork`:

- `codex/fix-document-asset-worktree`
- `codex/pr1-publishability-gate-config`
- `codex/pr2-external-controller-docs`
- `codex/upstream-evidence-packets`
- `codex/upstream-paper-artifact-delta`
- `codex/upstream-publishability-stop-loss`
- `codex/upstream-read-cache-telemetry`
- `codex/upstream-runner-diagnostics`
- `codex/upstream-runtime-log-hygiene`
- `codex/upstream-runtime-storage-maintenance`

Post-cleanup checks:

- `gh pr list --repo ResearAI/DeepScientist --author gaofeng21cn --state open --json number,title,url` -> `[]`
- `git ls-remote --heads pr-fork 'codex/*'` -> no heads

## Outcome

This round did not bulk-sync upstream.

The single MDS runtime absorption is the canonical summary mirror for explicit `artifact.refresh_summary(...)` calls. Other upstream movement is recorded as already-covered, watch-only, not-applicable, or rejected product breadth.

## Verification

MDS verification:

```bash
PYTHONPATH=src uv run pytest -q tests/test_memory_and_artifact.py -k 'refresh_summary'
git diff --check
```

