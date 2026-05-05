# Upstream Intake Guide

This document defines how MedDeepScientist (`med-deepscientist` 仓库) absorbs upstream `DeepScientist` changes without losing runtime stability for `MedAutoScience`.

## Core Rule

Upstream changes must enter through a dedicated intake worktree, pass fork-level regression and `MedAutoScience` compatibility regression, then be recorded in the medical fork audit surface before they can reach `main`.

This workflow exists to filter occasional upstream changes. It is not the primary development loop for this repository.

## Active Intake Audits

- [`docs/upstream_intake_round_2026_04_01.md`](./upstream_intake_round_2026_04_01.md): first audited upstream intake split for the current `behind_count=7` gap against `upstream/main`
- [`docs/upstream_intake_round_2026_04_19.md`](./upstream_intake_round_2026_04_19.md): targeted runtime and launcher hardening intake for stalled-turn recovery, Codex provider compatibility, and launcher management diagnostics
- [`docs/upstream_intake_round_2026_04_19_followup.md`](./upstream_intake_round_2026_04_19_followup.md): follow-up classification for publishability-gate policy drift and partial backend-only absorption from the baseline-compare preview bundle
- [`docs/upstream_intake_round_2026_04_20.md`](./upstream_intake_round_2026_04_20.md): UI build alignment, quest lazy-load intake, zombie-turn reconciliation, and branch cleanup on `main`
- [`docs/upstream_intake_round_2026_04_20_followup.md`](./upstream_intake_round_2026_04_20_followup.md): follow-up classification confirming the remaining valuable slices as frontend circular-safe serialization and TUI quest-browser key handling
- [`docs/upstream_intake_round_2026_04_28.md`](./upstream_intake_round_2026_04_28.md): latest-update learning round for path-aware file search, durable start-setup planning patches, manuscript coverage validation, duplicate evidence ledger selection, and bounded await discipline
- [`docs/upstream_intake_round_2026_04_30.md`](./upstream_intake_round_2026_04_30.md): latest-update learning round for academic outline gates, paper-outline workflow, paper-quality review prompts, runner evidence packets, log hygiene, and provider/UI deferrals
- [`docs/upstream_intake_round_2026_05_05.md`](./upstream_intake_round_2026_05_05.md): latest-update learning round for quest-root summary mirroring, upstream PR branch cleanup, and BenchStore/Nature/UI/product deferrals

## Remote Convention

This repository treats remotes explicitly:

- `origin`: canonical MedDeepScientist (`med-deepscientist`) GitHub repository
- `upstream`: upstream `DeepScientist` repository used for intake comparison

Do not overload `origin` to mean upstream. Controlled-fork auditing in `MedAutoScience` compares this repository against `upstream/main`.

## Why This Exists

MedDeepScientist (`med-deepscientist` 仓库) is not a mirror. It is a controlled fork whose job is to stabilize execution truth while `MedAutoScience` converges runtime protocol and retires implicit adapter assumptions.

That means upstream changes are only useful when they satisfy all of these:

- they solve a real runtime problem we care about
- they preserve the compatibility contract that `MedAutoScience` depends on
- they leave a durable audit trail in this repository

## Intake Cadence

Do not inspect upstream commit-by-commit just because `upstream/main` moved.

By default, upstream intake should happen only when at least one of these is true:

- a concrete upstream runtime fix appears likely to reduce real compatibility cost
- a maintainer explicitly starts a periodic upstream review round
- a specific upstream PR / commit bundle has already been identified as valuable
- a local bug or migration blocker points to a bounded upstream fix worth absorbing

When the maintainer says “学习一下 `DeepScientist` 的最新更新”, “看看 `DeepScientist` 最近更新有什么值得吸收”, or a similar periodic-learning phrase, treat it as an explicit upstream review round. The expected outcome is not a read-only summary: audit the fresh upstream delta, classify candidates, land bounded valuable slices in isolated worktrees, verify both fork-local and `MedAutoScience` contract surfaces, merge back to `main`, and clean temporary worktrees / branches.

The `MedAutoScience` owner-side trigger protocol lives in:

- `med-autoscience/docs/program/deepscientist_latest_update_learning_protocol.md`

Use that protocol to decide whether a change should become an `MDS` code slice, a `MAS` contract/template update, `watch_only`, or `reject`.

The main delivery stream remains:

- improving `MedAutoScience -> MedDeepScientist` compatibility
- converging the runtime protocol and transport boundary
- reducing adapter and layout coupling

## Intake Policy

Prefer:

- deterministic runtime bugfixes
- daemon correctness fixes
- document asset / worktree resolution fixes
- changes that preserve daemon API shape and quest/worktree layout

Review carefully before accepting:

- daemon API payload/status changes
- quest/worktree/paper/result layout changes
- workflow or prompt orchestration changes
- large dependency / lock refreshes

Reject by default:

- advertising or traffic-driving prompt edits
- unreviewed strategy rewrites
- changes that silently expand the compatibility surface

## Standard Intake Procedure

### 1. Keep the repository root on `main`

Do not perform intake work directly in the root checkout.

Create a worktree:

```bash
cd <med-deepscientist-root>
git fetch upstream
git worktree add .worktree/intake-2026-03-31-daemon-fix -b intake/2026-03-31-daemon-fix
```

### 2. Ask `MedAutoScience` whether intake is appropriate

Run the upgrade gate from `med-autoscience` first:

```bash
cd <med-autoscience-root>
PYTHONPATH=src python3 -m med_autoscience.cli deepscientist-upgrade-check --profile /path/to/profile.toml --refresh
```

This separates:

- upstream has moved
- we are ready to absorb it

### 3. Select specific upstream commits

Do not bulk-sync an arbitrary upstream window.
Do not treat every new upstream commit as an intake candidate worth detailed study.

Record for each candidate:

- upstream commit SHA
- kind
- expected benefit
- compatibility risk

Preferred default:

```bash
git cherry-pick <upstream-commit>
```

### 4. Run fork-local verification

At minimum, run the tests directly related to the absorbed change.

Example for daemon/document asset fixes:

```bash
PYTHONPATH=src pytest -q tests/test_daemon_api.py -k 'document_asset_resolves_path_documents_from_active_worktree'
```

### 5. Run `MedAutoScience` compatibility verification

The fork is not considered safe just because this repository passes.

Run `med-autoscience` regression against the current fork, especially if the intake touched:

- runtime behavior
- daemon API
- worktree / paper / artifact layout
- document assets

### 6. Update the fork audit surface

Every successful intake must update:

- [`MEDICAL_FORK_MANIFEST.json`](../MEDICAL_FORK_MANIFEST.json)
- [`docs/medical_fork_baseline.md`](./medical_fork_baseline.md)

For each absorbed commit, record:

- `commit`
- `kind`
- `summary`
- verification evidence

### 7. Only then merge back to `main`

An intake branch may return to `main` only when:

- fork regression passes
- `MedAutoScience` compatibility regression passes
- manifest and baseline documents are updated
- no unexplained API/layout drift remains

## Required Audit Surfaces

### `MEDICAL_FORK_MANIFEST.json`

Every absorbed commit should appear in `applied_commits`.

Example:

```json
{
  "commit": "d4994dba3ae1720a60daa7c80f5043f3722f32d8",
  "kind": "runtime_bugfix",
  "summary": "Fix worktree document asset resolution"
}
```

### `docs/medical_fork_baseline.md`

This is the human-readable changelog for the controlled fork. Record:

- commit
- kind
- reason
- verification command

## Forbidden Moves

- editing the root checkout directly and treating it as intake state
- merging `upstream/main` blindly into `main`
- accepting prompt ads or workflow changes without review
- changing daemon API or quest/worktree layout without compatibility analysis
- declaring intake complete without `MedAutoScience` regression

## Companion Document

The governance-side view of the same process lives in:

- `med-autoscience/guides/upstream_intake.md`
