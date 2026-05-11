# MedDeepScientist

MedDeepScientist (`med-deepscientist` repo) is no longer the default runtime dependency for `MedAutoScience`.

The repository started from a controlled DeepScientist fork. After the 2026-05-08 MAS functional monolith closeout, its current role is frozen source archive, historical fixture, explicit legacy diagnostic target, and upstream intake reference. MAS default study operation, status/progress/cockpit, diagnostics, artifact/quality parity, Progress Portal, and OPL handoff are now owned by `med-autoscience` and must not require this checkout, daemon, runtime root, or WebUI.

This repo remains useful when maintainers need source provenance, behavior fixture comparison, legacy restore/import diagnostics, or a fresh upstream DeepScientist intake review.

## What It Is Now

MedDeepScientist currently carries four responsibilities:

- preserve the frozen MDS source snapshot and attribution/license context
- provide historical quest / daemon / durable workspace behavior fixtures
- support explicit legacy restore/import or backend-audit diagnostics when requested
- absorb or document useful upstream changes only as MAS source intake/reference material

## Why It Exists

Upstream DeepScientist moves quickly across prompts, skills, workflows, connectors, and product surfaces. `MedAutoScience` now owns the default runtime, progress, quality, artifact, and diagnostic surfaces in one monolith; this repo remains the controlled place to inspect or compare upstream-derived behavior without bringing upstream history or contributor footprint into MAS.

MedDeepScientist gives the stack a place to:

- keep the frozen source and legacy behavior inspectable
- run explicit diagnostic checks against old MDS semantics when needed
- preserve useful upstream lessons without sweeping in broad product churn
- make every future source intake auditable and reversible

## Stack Relationship

- `DeepScientist`: upstream capability source
- `MedDeepScientist`: frozen source archive, historical fixture, legacy diagnostic target, and audited intake reference
- `MedAutoScience`: default monolith for runtime, orchestration, policy, controller, progress, quality, artifact, and medical entrypoint

Medical users should enter through `MedAutoScience`. This repository is not the default runtime layer underneath MAS.

```text
human / automation
        ->
MedAutoScience
        ->
MAS Runtime OS / Artifact OS / Quality OS
        ->
optional legacy diagnostic / historical fixture reference
```

## Current Execution Truth

The current MAS default execution truth is in `med-autoscience`: `mas_runtime_core` implements the controller-facing runtime backend contract and records MAS-owned local runtime state/events. It does not start the MDS daemon.

This repository can still run its own fork-local daemon and UI for maintenance or legacy inspection, but that is no longer MAS default operation or diagnostic truth.

## What This Repo Owns

The repository is responsible for keeping these surfaces explicit and auditable:

- runtime identity and fork metadata
- legacy daemon API shape and behavior fixtures
- legacy quest layout and durable workspace layout fixtures
- source provenance, license, and upstream intake records
- controlled upstream intake workflow

## Long-Line Direction

The long-line target is specific: keep this repo as a frozen/reference lane unless a future source intake produces a bounded MAS-owned capability.

We are converging toward:

- no MAS default dependency on this checkout, daemon, runtime root, or WebUI
- explicit source provenance and behavior fixture references
- no upstream DeepScientist contributor history imported into `med-autoscience`
- future upstream intake flowing into MAS only through no-history, MAS-authored capability proof
- compatibility shells that retire on evidence instead of guesswork

The engineering goal is lower maintenance cost, clear provenance, and selective MAS-owned capability absorption.

## Upstream Intake

We continue to absorb valuable upstream work.

The intake rule is simple:

1. inspect the upstream delta against current `MedAutoScience` needs
2. absorb only the bounded slice that has clear runtime value
3. run focused fork-local regression
4. run compatibility verification against the final merged state
5. update audit surfaces and close the worktree quickly

Useful intake candidates usually fall into these buckets:

- deterministic runtime correctness fixes
- packaging and operator reliability fixes
- narrow daemon / runner / durable-layout improvements
- documentation or contract clarifications that remove ambiguity

See:

- [docs/upstream_intake.md](docs/upstream_intake.md)
- [docs/medical_fork_baseline.md](docs/medical_fork_baseline.md)
- [MEDICAL_FORK_MANIFEST.json](MEDICAL_FORK_MANIFEST.json)

## Compatibility Names

Public identity and compatibility shells currently coexist:

- public project name: `MedDeepScientist`
- Python package/import namespace: `deepscientist`
- launcher command: `ds`
- default runtime home: `~/DeepScientist`

These names stay in place while the runtime contract and family entrypoints continue to converge.

## Documentation

- [中文 README](README.zh-CN.md)
- [Docs index](docs/README.md)
- [Project overview](docs/project.md)
- [Current status](docs/status.md)
- [Architecture](docs/architecture.md)
- [Invariants](docs/invariants.md)
- [Decisions](docs/decisions.md)
- [Stable runtime protocol](docs/policies/runtime_protocol.md)
- [Runner contract](docs/policies/runner_contract.md)
- [System visibility contract](docs/policies/system_visibility_contract.md)
- [Windows + WSL2 deployment guide](docs/en/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)
- [English docs index](docs/en/README.md)
- [Chinese docs index](docs/zh/README.md)

## If You Are Here To Use The Medical Stack

Start from `MedAutoScience`.

MedDeepScientist is a maintainer-facing archive / diagnostic / upstream intake reference.

## License and Attribution

This repository remains Apache-2.0 and builds on the DeepScientist open-source codebase.
