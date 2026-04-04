# MedDeepScientist

MedDeepScientist (`med-deepscientist` repo) is a controlled runtime fork of [DeepScientist](https://github.com/ResearAI/DeepScientist).

It exists to preserve the long-running autonomous runtime that `MedAutoScience` depends on, because upstream changes in prompts, skills, workflow defaults, or runtime surfaces tend to trigger expensive compatibility work for medical workspaces. Freezing a known-good baseline and accepting only audited intake keeps that runtime truth stable while MedAutoScience converges on a narrower runtime protocol.

The primary engineering priority is not to follow upstream continuously. The primary engineering priority is to make `MedDeepScientist` a cleaner, narrower, and more stable runtime for `MedAutoScience`, so the medical stack can reduce adapter debt and rely on an explicit runtime protocol.

This repository is not a hostile rewrite of DeepScientist. It is a thin, audited fork that:

- freezes a known-good upstream baseline
- records every absorbed patch in machine-readable and human-readable audit surfaces
- accepts upstream changes only through a controlled intake workflow
- keeps the runtime behavior stable while `MedAutoScience` converges on a narrower runtime protocol


## Agent 合同分层

<!-- AGENT-CONTRACT-BASELINE:START -->
- 根目录 `AGENTS.md` 仅用于本仓库开发环境中的 Codex/OMX 协作，不单独承载项目真相合同
- 宿主适配层位于 `contracts/dev-hosts/`，用于区分 OMX CLI 与 Codex App / plain Codex 的开发宿主行为
- 项目真相合同位于 `contracts/project-truth/AGENTS.md`
- 可选本机私有覆盖层约定为 `.omx/local/AGENTS.local.md`，保持未跟踪
- 本地工具运行态目录 `.omx/` 与 `.codex/` 必须保持未跟踪，不进入版本库
<!-- AGENT-CONTRACT-BASELINE:END -->

## Why this fork exists

Upstream DeepScientist is strong at exactly the capability we want to keep:

- long-running autonomous execution
- bounded-task persistence with little human intervention
- quest/worktree based durable state
- a real runtime instead of a stateless chat wrapper

But upstream DeepScientist is optimized as a fast-moving product for frontier AI research workflows, not as a high-compatibility downstream runtime contract.

For a medical research operating layer, that creates unnecessary cost:

- prompt changes can alter manuscript-facing behavior
- skill changes can break downstream overlays or policy assumptions
- runtime/layout changes can invalidate controller expectations
- undocumented workflow drift can turn a normal upgrade into a migration project

MedDeepScientist exists to cap that cost.

## Relationship to the rest of the stack

- `DeepScientist`: upstream source of runtime capability and future improvements
- `MedDeepScientist`: controlled runtime fork used as the stable execution engine
- `MedAutoScience`: medical orchestration layer, policy layer, controller layer, and public entrypoint

For medical workflows, humans and agents should enter through `MedAutoScience`, not through legacy DeepScientist entrypoints directly.

The intended stack is:

```text
human / automation
        ->
MedAutoScience
        ->
runtime_protocol / runtime_transport
        ->
MedDeepScientist (`med-deepscientist` repo)
        ->
quest runtime / daemon / worktrees
```

## What is stable here

The minimal stable runtime surface is defined by [`docs/policies/runtime_protocol.md`](docs/policies/runtime_protocol.md). When this README conflicts with implementation details, treat that protocol spec as authoritative for `MedAutoScience` adapter compatibility.

This repository is responsible for keeping these boundaries explicit and auditable:

- upstream freeze baseline
- runtime identity and fork metadata
- daemon API shape expected by `MedAutoScience`
- quest layout and worktree layout
- controlled intake process for upstream absorption

It is intentionally not trying to become a second full product strategy on top of upstream.

## Sustained evolution

MedAutoScience and MedDeepScientist evolve together:

- the runtime stays restrained by compatibility contracts and documented intake so that every patch carries verifiable value
- the medical orchestration layer iterates on controllers, overlays, policies, and runtime protocol while keeping the runtime view clear
- the main line of work is improving `MedAutoScience -> MedDeepScientist` compatibility and removing unnecessary adapter assumptions
- valuable upstream improvements continue to flow in when they pass intake, regression, and audit checks rather than being swept in wholesale

This dual track lets us keep improving the runtime while still absorbing useful upstream work without forcing downstream teams to constantly requalify their workspaces.

## Naming and compatibility policy

The public project name is now `MedDeepScientist` (repository `med-deepscientist`).

To avoid breaking active integrations too early, several internal compatibility shells remain in place for now:

- Python package/import namespace: `deepscientist`
- launcher command: `ds`
- default runtime home: `~/DeepScientist`

Those legacy names are treated as compatibility surfaces, not as the long-term public project identity.

## Upstream intake policy

We still want useful upstream improvements.

The rule is not "never sync upstream". The rule is "never sync upstream blindly".

It is also not "inspect every upstream commit one by one".

Most upstream commits do not deserve immediate engineering time in this fork. Intake is a periodic, trigger-based maintenance action, not the main delivery stream.

When upstream ships a change that is actually valuable, we try to absorb it through the documented intake flow:

1. inspect the upstream delta from `MedAutoScience`
2. absorb only selected commits or a clearly bounded change set
3. run fork-local regression
4. run `MedAutoScience` compatibility regression
5. update the audit surfaces
6. only then let the change return to the stable line

In practice, we prefer to spend time on:

- runtime compatibility with `MedAutoScience`
- runtime protocol convergence
- adapter retirement and boundary cleanup
- deterministic runtime correctness fixes

We only start a new intake round when there is a bounded upstream change set with clear runtime value, or when we intentionally run a periodic upstream review.

That means we keep benefiting from upstream progress without forcing every downstream medical workspace to act like a canary.

See:

- [docs/upstream_intake.md](docs/upstream_intake.md)
- [docs/medical_fork_baseline.md](docs/medical_fork_baseline.md)
- [MEDICAL_FORK_MANIFEST.json](MEDICAL_FORK_MANIFEST.json)

## Current roadmap

### Phase 1

- freeze a usable upstream baseline
- carry only audited bugfixes and compatibility fixes
- expose controlled-fork metadata to `MedAutoScience`

### Phase 2

- converge `MedAutoScience` onto a narrow runtime protocol
- reduce implicit assumptions about upstream skill precedence and adapter behavior
- keep runtime truth stable while controller truth moves upward

### Phase 3

- retire unnecessary legacy coupling
- make the public identity fully consistent with MedDeepScientist
- keep upstream intake sustainable instead of ad hoc

## Documentation

- [Docs index](docs/README.md)
- [Minimal stable runtime protocol](docs/policies/runtime_protocol.md)
- [English docs index](docs/en/README.md)
- [中文文档索引](docs/zh/README.md)
- [Upstream intake workflow](docs/upstream_intake.md)
- [Fork baseline and audit log](docs/medical_fork_baseline.md)
- [Maintainer architecture reference](docs/en/90_ARCHITECTURE.md)
- [Maintainer development guide](docs/en/91_DEVELOPMENT.md)

## If you are here to use the medical stack

Start from `MedAutoScience`.

This repository is the runtime layer under it, not the recommended top-level medical entrypoint.

## License and attribution

This repository remains an Apache-2.0 project and builds on the upstream DeepScientist open-source codebase.
