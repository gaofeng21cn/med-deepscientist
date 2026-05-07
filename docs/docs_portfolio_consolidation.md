# Docs Portfolio Consolidation

## Current Truth

`MedDeepScientist` is the MAS-controlled runtime/backend companion for long-running quest execution, runtime compatibility, behavior-oracle checks, and audited upstream intake.

It is not an OPL default active domain agent, and it is not the default medical research product entry. Medical study intake, publication readiness, submission authority, medical evidence interpretation, and user-visible study progress remain owned by `MedAutoScience`.

## Portfolio Tiers

- Core truth: `docs/project.md`, `docs/architecture.md`, `docs/invariants.md`, `docs/decisions.md`, and `docs/status.md`.
- Policies: `docs/policies/`, including stable runtime protocol, MAS/MDS transition rules, runner/system-visibility contracts, and native runtime truth rules.
- References: `docs/references/`, including controlled-fork baselines, current upstream intake procedure, and owner-split audits.
- History: `docs/history/`, including completed intake rounds and retired process records.
- User-facing guide corpus: `docs/en/` and `docs/zh/`, inherited from upstream-facing documentation and kept for operator/user workflows.

Repo-specific MAS/MDS transition truth belongs in core, policies, and references. The bilingual `docs/en/` and `docs/zh/` trees may mention current runtime behavior, but they do not define MAS/MDS ownership or promotion authority.

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
