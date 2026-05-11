# MedDeepScientist Docs

MedDeepScientist (`med-deepscientist` repo) is no longer the default runtime substrate for `MedAutoScience`.

This repository began as a controlled runtime fork and now serves a narrower role: frozen source archive, historical fixture, explicit legacy diagnostic target, and audited upstream intake reference. `MedAutoScience` owns the default runtime, progress, quality, artifact, and medical product entry surfaces after the MAS functional monolith closeout.

This docs index is for the archive / diagnostic / intake repository itself. Medical users should start from `MedAutoScience`. This repository matters when maintainers need to understand:

- why the old runtime fork is still inspectable
- what legacy diagnostic and behavior-fixture boundaries remain
- how upstream `DeepScientist` changes are reviewed safely
- which inherited runtime behaviors are retained only for maintenance, parity, or intake reference

## Corpus Boundary

`docs/en/` is an upstream/user-facing guide corpus for fork-local operator workflows. It can explain inherited `DeepScientist` behavior, compatibility names, maintenance commands, and legacy diagnostic surfaces, but it does not define MAS owner truth, MAS default runtime dependency, MAS product entry semantics, publication authority, artifact authority, or user-visible study progress.

Use these owner surfaces instead:

- MAS owner truth and medical product entry semantics: `MedAutoScience`
- MDS archive/reference boundary: [Project Overview](../project.md), [Current Status](../status.md), and [Architecture](../architecture.md)
- Stable legacy diagnostic protocol: [Stable Runtime Protocol](../policies/runtime_protocol.md)
- MAS/MDS boundary contraction: [MAS/MDS Transition Contract](../policies/mas_mds_transition_contract.md)
- Upstream intake procedure: [Upstream Intake Guide](../references/upstream_intake.md)

Compatibility names currently remain:

- Python package: `deepscientist`
- CLI: `ds`
- npm package: `@researai/deepscientist`

## Start Here

- [Stable Runtime Protocol](../policies/runtime_protocol.md)
  The authoritative fork-local protocol for legacy diagnostic and behavior-fixture work.
- [Repository README](../../README.md)
  Project positioning, fork rationale, architecture, and compatibility policy.
- [Fork Baseline](../references/medical_fork_baseline.md)
  Human-readable freeze baseline and applied patch history.
- [Upstream Intake Guide](../references/upstream_intake.md)
  The required process for absorbing upstream `DeepScientist` changes.

## Runtime Maintenance

- [90 Architecture](./90_ARCHITECTURE.md)
  High-level system contracts and repository structure.
- [91 Development](./91_DEVELOPMENT.md)
  Maintainer-facing workflow and implementation notes.
- [22 Windows WSL2 Deployment Guide](./22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)
  The Windows operator path that matches this fork and points AI agents at the current setup skill.
- [Windows WSL2 setup skill](../../src/skills/windows-wsl2-setup/SKILL.md)
  The executable install and repair workflow for AI coding agents working from this repo.
- [09 Doctor](./09_DOCTOR.md)
  Startup diagnostics and runtime repair.
- [01 Settings Reference](./01_SETTINGS_REFERENCE.md)
  Runtime configuration and environment settings.
- [22 BenchStore YAML Authoring Guide](./22_BENCHSTORE_YAML_REFERENCE.md)
  Maintainer-facing catalog authoring contract for the current BenchStore surface.
- [23 BenchStore GitHub Releases Spec](./23_BENCHSTORE_GITHUB_RELEASES_SPEC.md)
  Recommended source-bundle release contract for BenchStore benchmark assets.

## Inherited Runtime Surfaces

These documents still describe fork-local runtime behavior preserved for maintenance and legacy inspection:

- [05 TUI Guide](./05_TUI_GUIDE.md)
- [06 Runtime and Canvas](./06_RUNTIME_AND_CANVAS.md)
- [07 Memory and MCP](./07_MEMORY_AND_MCP.md)
- [13 Core Architecture Guide](./13_CORE_ARCHITECTURE_GUIDE.md)
- [14 Prompt, Skills, and MCP Guide](./14_PROMPT_SKILLS_AND_MCP_GUIDE.md)

## External Control Patterns

- [19 External Controller Guide](./19_EXTERNAL_CONTROLLER_GUIDE.md)
  How to build optional outer-orchestration guards on top of durable quest state, mailbox, and `quest_control`.

## Connector Runtime Guides

- [03 QQ Connector Guide](./03_QQ_CONNECTOR_GUIDE.md)
- [04 Lingzhu Connector Guide](./04_LINGZHU_CONNECTOR_GUIDE.md)
- [10 Weixin Connector Guide](./10_WEIXIN_CONNECTOR_GUIDE.md)
- [16 Telegram Connector Guide](./16_TELEGRAM_CONNECTOR_GUIDE.md)
- [17 WhatsApp Connector Guide](./17_WHATSAPP_CONNECTOR_GUIDE.md)
- [18 Feishu Connector Guide](./18_FEISHU_CONNECTOR_GUIDE.md)

## Note On Scope

`docs/en/` is the upstream/user-facing guide corpus for operator workflows. Repo-specific MAS/MDS transition truth lives in `docs/project.md`, `docs/architecture.md`, `docs/status.md`, `docs/policies/`, and `docs/references/`.

This repository stays narrower than upstream `DeepScientist`.

Its role is archive/reference guardianship, legacy diagnostic clarity, and audited capability intake. It is not an active OPL domain agent, not a MAS default dependency, and not the medical research product entry. OPL's current Codex-first, stage-led framework work only treats this repo as a MAS-declared optional provenance, oracle, or intake reference.
