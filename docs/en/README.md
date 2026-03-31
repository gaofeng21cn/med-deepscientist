# med-deepscientist Docs

`med-deepscientist` is the controlled runtime fork that `MedAutoScience` uses as its execution engine.

This docs index is for the runtime repository itself. Most medical users should start from `MedAutoScience`. This repository matters when you need to understand:

- why the runtime is forked
- what compatibility contract the fork preserves
- how upstream `DeepScientist` changes are absorbed safely
- how the inherited runtime still works underneath

Compatibility names currently remain:

- Python package: `deepscientist`
- CLI: `ds`
- npm package: `@researai/deepscientist`

## Start Here

- [Repository README](../../README.md)
  Project positioning, fork rationale, architecture, and compatibility policy.
- [Fork Baseline](../medical_fork_baseline.md)
  Human-readable freeze baseline and applied patch history.
- [Upstream Intake Guide](../upstream_intake.md)
  The required process for absorbing upstream `DeepScientist` changes.

## Runtime Maintenance

- [90 Architecture](./90_ARCHITECTURE.md)
  High-level system contracts and repository structure.
- [91 Development](./91_DEVELOPMENT.md)
  Maintainer-facing workflow and implementation notes.
- [09 Doctor](./09_DOCTOR.md)
  Startup diagnostics and runtime repair.
- [01 Settings Reference](./01_SETTINGS_REFERENCE.md)
  Runtime configuration and environment settings.

## Inherited Runtime Surfaces

These documents still describe the underlying runtime behavior that this fork currently preserves:

- [05 TUI Guide](./05_TUI_GUIDE.md)
- [06 Runtime and Canvas](./06_RUNTIME_AND_CANVAS.md)
- [07 Memory and MCP](./07_MEMORY_AND_MCP.md)
- [13 Core Architecture Guide](./13_CORE_ARCHITECTURE_GUIDE.md)
- [14 Prompt, Skills, and MCP Guide](./14_PROMPT_SKILLS_AND_MCP_GUIDE.md)

## Connector Runtime Guides

- [03 QQ Connector Guide](./03_QQ_CONNECTOR_GUIDE.md)
- [04 Lingzhu Connector Guide](./04_LINGZHU_CONNECTOR_GUIDE.md)
- [10 Weixin Connector Guide](./10_WEIXIN_CONNECTOR_GUIDE.md)
- [16 Telegram Connector Guide](./16_TELEGRAM_CONNECTOR_GUIDE.md)
- [17 WhatsApp Connector Guide](./17_WHATSAPP_CONNECTOR_GUIDE.md)
- [18 Feishu Connector Guide](./18_FEISHU_CONNECTOR_GUIDE.md)

## Note On Scope

This repository is deliberately narrower than upstream `DeepScientist`.

Its job is not to become a separate medical orchestration product. Its job is to provide a stable, auditable runtime layer so `MedAutoScience` does not have to continuously re-adapt to upstream compatibility drift.
