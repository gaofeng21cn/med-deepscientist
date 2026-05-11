# MedDeepScientist

`MedDeepScientist` 现在不是 `MedAutoScience` 的默认运行依赖，也不是医学研究产品入口。

这个仓库来自受控的 DeepScientist 分支。2026-05-08 MAS functional monolith 收口后，它的当前职责已经收窄为：冻结源码归档、历史行为 fixture、显式 legacy diagnostic target，以及上游 intake reference。MAS 的默认研究运行、状态/进度、质量、artifact、诊断、Progress Portal 和 OPL handoff 都由 `med-autoscience` 持有，不应要求本仓 checkout、daemon、runtime root 或 WebUI。

如果你是医学用户或研究操作者，请从 `MedAutoScience` 进入。这个仓库主要给维护者使用，用来查看旧源码来源、对比历史行为、做显式 legacy restore/import/backend-audit 诊断，或审查 upstream DeepScientist 中是否有值得 MAS 吸收的有限能力。

## 当前角色

- 保留冻结的 MDS 源码快照、license 和 provenance 背景。
- 保留旧 quest、daemon、durable workspace 行为 fixture。
- 支持显式 legacy restore/import/backend-audit diagnostic。
- 作为 upstream DeepScientist intake 的审计参考。

## 与 OPL/MAS 的关系

- `OPL` 是 Codex-first、stage-led 的完整智能体运行框架，可以把外部 domain agent 作为依赖接入。
- `Codex CLI` 是 OPL stage attempt 的最小执行单元，除非活跃合同显式选择其他 provider。
- `MedDeepScientist` 不是 OPL 当前 active domain agent、默认安装依赖或 stage adapter。
- `MedDeepScientist` 只会被 MAS 显式声明为 backend audit、source provenance、historical fixture、explicit archive import、upstream intake 或 parity oracle reference。

## 继续阅读

- [Docs index](docs/README.md)
- [项目概览](docs/project.md)
- [当前状态](docs/status.md)
- [架构](docs/architecture.md)
- [不变量](docs/invariants.md)
- [决策记录](docs/decisions.md)
- [MAS/MDS 迁移收缩契约](docs/policies/mas_mds_transition_contract.md)
