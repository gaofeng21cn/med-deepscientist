# Upstream Intake Audit 2026-04-19 Follow-up

This audit records the bounded follow-up intake work that happened after the main 2026-04-19 upstream round had already landed on `main`.

## Snapshot

- audit_date: `2026-04-19`
- target_repo: `MedDeepScientist` (repository `med-deepscientist`)
- comparison_ref: `upstream/main`
- fork_head_before_followup: `f4bf205`
- comparison_head: `13fa853`
- rev_list_main_vs_upstream: `ahead=119, behind=123`
- medautoscience_upgrade_gate: `upgrade_available`
- execution_status: `partial_backend_followup_absorbed_with_audit_surface_catchup`

## Evidence

This follow-up was classified from fresh local evidence:

```bash
git fetch upstream --prune
git rev-list --left-right --count main...upstream/main
git cherry -v main upstream/main
git show 9bd736d14357d5a453978b1755a99c80cd793988
git show 1865fa5e608e5ccc0f9b92ba72fc770791538847 -- src/deepscientist/artifact/metrics.py src/deepscientist/artifact/service.py
uv run python -m med_autoscience.cli backend-upgrade-check --profile <temporary-workspace-profile> --refresh
```

The `med-autoscience` backend upgrade gate was run against a temporary profile rooted at `/Users/gaofeng/workspace/Yang/DM-CVD-Mortality-Risk` and returned:

- `decision: upgrade_available`
- `recommended_actions: ["run_controlled_fork_intake_workflow"]`

## Candidate Decisions

### Candidate A: local publishability-gate patch

- source commit: `9bd736d14357d5a453978b1755a99c80cd793988`
- title: `feat: add explicit publishability gate mode`
- decision: `defer`
- rationale:
  - current `main` already treats `publication_gate` and paper-contract health as the single live paper-admission authority
  - adding `startup_contract.publishability_gate_mode = off|warn|enforce` would introduce a second gate authority inside the runtime seam
  - the patch conflicts directly with the current prompt-builder and write-skill contract, and it would also widen the startup-contract ownership surface without first updating the stable runtime protocol

This candidate stays outside `main` until gate authority is redesigned around one explicit owner.

### Candidate B: baseline compare / interaction preview bundle

- source commit: `1865fa5e608e5ccc0f9b92ba72fc770791538847`
- title: `feat: split baseline compare and interaction previews`
- decision: `absorb_partial`

The full upstream feature spans backend projections, daemon API, web details UI, prompt/skill wording, and preview semantics. That full bundle still widens the product surface too much for the controlled fork.

The absorbed backend-only slice is:

1. prefer baseline variant `label` over raw `variant_id` in `baseline_metric_lines()`
2. keep full connector-facing idea interaction text instead of truncating the substantive tail inline

The deferred remainder is:

- `build_baseline_compare_payload()`
- `QuestService.baseline_compare()`
- `/api/quests/{quest_id}/baselines/compare`
- Baseline Compare web UI and related demo/types work
- `summary_preview` split semantics
- prompt / skill / docs coupling from the full feature

### Candidate C: workspace mode / continuation policy bundle

- source commits:
  - `7c9c03f3dc9bcce433b4f16993735ff3505e6861`
  - `d58a65584fc7e958f2363e9110c726823b64a4e2`
  - `d9d4bd6b8b9654f4409eb7ff673c9ecadc301cbf`
- title: `workspace mode switch and continuation-policy reconciliation`
- decision: `defer_incompatible`
- rationale:
  - upstream uses `workspace_mode` for the runtime control surface `copilot | autonomous`
  - current fork already uses `research_state.workspace_mode` as a research worktree state namespace with values such as `quest | idea | analysis | paper | run`
  - absorbing the upstream bundle would overload one persisted field with two unrelated authorities and would corrupt the current artifact/worktree routing seam
  - the continuation-policy logic in those commits depends on that upstream mode meaning, so the safe follow-up path is a future dedicated controller/runtime contract design instead of a direct intake

## Execution Result

The backend-only follow-up was absorbed as:

- local commit: `223f086`
- title: `Refine baseline labels and idea interaction text`

This follow-up also repaired the fork audit surface so it now records previously landed intake commits that had already reached `main`:

- `fcba71f` `Fix corrupted older event history pagination`
- `838f87e` `feat: improve runtime recovery diagnosis`
- `a255de4` `Harden Windows asset and git subprocess handling`

## Verification

The absorbed backend-only slice passed fresh verification in the dedicated intake worktree:

```bash
uv run pytest -q tests/test_metrics_overview_surface.py
uv run pytest -q tests/test_memory_and_artifact.py -k idea_interaction_message
scripts/verify.sh
git diff --check
```

Key outcomes:

- `tests/test_metrics_overview_surface.py`: `5 passed`
- `tests/test_memory_and_artifact.py -k idea_interaction_message`: `2 passed, 126 deselected`
- `scripts/verify.sh`: `55 passed`
- `git diff --check`: clean
