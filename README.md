# MedDeepScientist

MedDeepScientist (`med-deepscientist` repo) is the stable runtime substrate that `MedAutoScience` uses for long-running autonomous medical research execution.

The repository started from a controlled DeepScientist fork. Today it serves a broader and clearer role: it is the audited runtime surface where we preserve durable quest execution, tighten the `MedAutoScience -> MedDeepScientist` contract, and selectively absorb upstream improvements that carry clear runtime value.

The long-line target is a family runtime surface with lower compatibility cost, clearer ownership boundaries, and less adapter debt. This repository remains the current delivery vehicle for that work.

## What It Is Now

MedDeepScientist currently carries four responsibilities:

- provide the stable quest / daemon / durable workspace runtime that `MedAutoScience` depends on
- preserve the long-horizon execution loop inherited from DeepScientist
- narrow the runtime protocol and document it as an explicit compatibility contract
- absorb useful upstream changes through audited intake, focused regression, and fast closeout

## Why It Exists

Upstream DeepScientist moves quickly across prompts, skills, workflows, connectors, and product surfaces. `MedAutoScience` needs a steadier runtime seam so medical workspaces can keep running without paying a migration cost every time the upstream product shifts.

MedDeepScientist gives the stack a place to:

- keep runtime truth durable and inspectable
- retire implicit adapter assumptions with tests and policy docs
- preserve useful upstream capabilities without sweeping in broad product churn
- make every absorbed change auditable and reversible

## Stack Relationship

- `DeepScientist`: upstream capability source
- `MedDeepScientist`: runtime substrate and audited intake surface
- `MedAutoScience`: orchestration, policy, controller, and medical entrypoint

Medical users should enter through `MedAutoScience`. This repository is the runtime and compatibility layer underneath.

```text
human / automation
        ->
MedAutoScience
        ->
runtime protocol / runtime transport
        ->
MedDeepScientist
        ->
quest runtime / daemon / worktrees / artifact surfaces
```

## Current Execution Truth

The current default execution chain is:

`daemon API -> RunRequest -> CodexRunner -> codex exec autonomous agent loop`

Current runtime facts:

- default runner: `codex`
- default model / reasoning: inherit from the local Codex configuration
- opt-in proof lane: `hermes_native_proof`
- reserved experimental runner ids: `claude`, `opencode`
- stable compatibility spec: [`docs/policies/runtime_protocol.md`](docs/policies/runtime_protocol.md)

This means the repo tracks a stable runtime contract first, then selected execution surfaces that fit that contract.

## What This Repo Owns

The repository is responsible for keeping these surfaces explicit and auditable:

- runtime identity and fork metadata
- daemon API shape used by `MedAutoScience`
- quest layout and durable workspace layout
- runtime-owned artifact truth
- runner metadata and executor contract boundaries
- controlled upstream intake workflow

## Long-Line Direction

The long-line target is more specific than “keep a frozen fork alive”.

We are converging toward:

- a narrow and explicit family runtime protocol
- fewer repo-local adapter assumptions in `MedAutoScience`
- clearer ownership split: runtime truth stays here, orchestration and product behavior live higher in the stack
- compatibility shells that can retire on evidence instead of guesswork
- a flexible repo boundary: this repository can remain the audited runtime surface, or later fold into a family mainline when that creates a cleaner operational model

The engineering goal is steady contract convergence, lower maintenance cost, and selective capability absorption.

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

MedDeepScientist is the runtime substrate and maintainer-facing compatibility surface under it.

## License and Attribution

This repository remains Apache-2.0 and builds on the DeepScientist open-source codebase.
