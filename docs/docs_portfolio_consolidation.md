# Docs Portfolio Consolidation

## Current Truth

`MedDeepScientist` is the frozen source archive, historical fixture, explicit legacy diagnostic target, and audited upstream intake reference for the former MAS/MDS split.

It is not an OPL default active domain agent, not an OPL default dependency, not an OPL stage adapter, not the default MAS runtime backend, and not the default medical research product entry. Medical study intake, runtime status/progress, publication readiness, submission authority, medical evidence interpretation, artifact truth, and user-visible study progress are owned by `MedAutoScience`.

## Portfolio Tiers

- Core truth: `docs/project.md`, `docs/architecture.md`, `docs/invariants.md`, `docs/decisions.md`, and `docs/status.md`.
- Policies: `docs/policies/`, including stable runtime protocol, MAS/MDS transition rules, runner/system-visibility contracts, and native runtime truth rules.
- References: `docs/references/`, including controlled-fork baselines, current upstream intake procedure, and owner-split audits.
- History: `docs/history/`, including completed intake rounds and retired process records.
- User-facing guide corpus: `docs/en/` and `docs/zh/`, inherited from upstream-facing documentation and kept for operator/user workflows.

Repo-specific MAS/MDS transition truth belongs in core, policies, and references. The bilingual `docs/en/` and `docs/zh/` trees preserve fork-local user/operator guide corpus, but they do not define MAS/MDS ownership, MAS default runtime dependency, or promotion authority.

## Root Docs Governance Allowlist

Root-level files under `docs/` are limited to:

- core truth documents
- `docs/README.md`
- this portfolio consolidation note
- thin compatibility pointers for paths that existed before consolidation

The canonical locations are:

- `docs/references/medical_fork_baseline.md`
- `docs/policies/runtime_native_truth_and_outer_loop_input_contract.md`
- `docs/references/upstream_intake.md`

The legacy root paths remain as human-readable compatibility pointers only. They do not create a second truth source.

## Human And Machine Surfaces

`README*` and `docs/**` are human-readable surfaces. Tests, runtime reports, schemas, dashboards, and controllers may point to them with human-context identifiers, but machine contracts must use structured surfaces, schemas, reports, or explicit policy IDs. They must not pin prose wording, Markdown section text, or `docs/**/*.md` paths as compatibility contracts.

## Lifecycle Rule

Classify documents by content, not by filename. Any guide that still describes MedDeepScientist as the MAS default runtime substrate must be read as upstream/user-facing guide corpus or historical diagnostic context unless a core truth document explicitly promotes it. Current public and maintainer entry points must say that MAS owns default runtime/product authority, OPL is the Codex-first stage-led framework with Codex CLI as the minimum execution unit, and this repo is archive/reference/diagnostic/intake only.
