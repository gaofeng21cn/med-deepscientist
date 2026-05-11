# MedDeepScientist 文档总览

MedDeepScientist（`med-deepscientist` 仓库）不再是 `MedAutoScience` 的默认运行底座。

这个仓库起点是一个受控 runtime fork，现在的角色已经收窄为冻结源码归档、历史行为 fixture、显式 legacy diagnostic target 与受审计的上游 intake reference。MAS functional monolith closeout 后，默认运行、进度、质量、artifact 和医学产品入口都由 `MedAutoScience` 持有。

这份文档索引面向 archive / diagnostic / intake 仓库本身。医学用户应该从 `MedAutoScience` 进入；这个仓库主要帮助维护者判断：

- 为什么旧 runtime fork 仍需要可检查
- 还保留哪些 legacy diagnostic 和 behavior fixture 边界
- 上游 `DeepScientist` 更新应该怎样被安全审查
- 哪些继承 runtime 行为只用于维护、parity 或 intake reference

当前仍保留这些兼容名字：

- Python package：`deepscientist`
- CLI：`ds`
- npm package：`@researai/deepscientist`

## 建议先看

- [稳定 Runtime Protocol](../policies/runtime_protocol.md)
  legacy diagnostic 和 behavior fixture 工作使用的 fork-local 稳定协议。
- [仓库 README](../../README.md)
  项目定位、fork 原因、架构关系与兼容策略。
- [Freeze Baseline](../references/medical_fork_baseline.md)
  受控 fork 的冻结基线和已吸收补丁记录。
- [上游 Intake 指南](../references/upstream_intake.md)
  如何把上游 `DeepScientist` 更新吸收到这个 fork。

## Runtime 维护

- [90 Architecture](../en/90_ARCHITECTURE.md)
  系统级约束与仓库结构。
- [91 Development](../en/91_DEVELOPMENT.md)
  面向维护者的开发与验证流程。
- [22 Windows WSL2 部署指南](./22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)
  面向 Windows 操作机器的 WSL2 部署路径，并指向当前仓库可执行的 setup skill。
- [Windows WSL2 安装 skill](../../src/skills/windows-wsl2-setup/SKILL.md)
  面向 AI coding agent 的 Windows + WSL2 安装、修复与验证流程。
- [09 启动诊断](./09_DOCTOR.md)
  启动和运行时修复入口。
- [01 设置参考](./01_SETTINGS_REFERENCE.md)
  运行时配置与环境设置。
- [22 BenchStore YAML 编写指南](./22_BENCHSTORE_YAML_REFERENCE.md)
  面向维护者的 catalog authoring 合同。
- [23 BenchStore GitHub Releases 分发规范](./23_BENCHSTORE_GITHUB_RELEASES_SPEC.md)
  面向维护者的 BenchStore benchmark 源码包发布合同。

## 当前继承的 Runtime 行为

下面这些文档仍然描述了这个 fork 为维护和 legacy inspection 保留的底层 runtime 行为：

- [05 TUI 指南](./05_TUI_GUIDE.md)
- [06 Runtime 与 Canvas](./06_RUNTIME_AND_CANVAS.md)
- [07 Memory 与 MCP](./07_MEMORY_AND_MCP.md)
- [13 核心架构说明](./13_CORE_ARCHITECTURE_GUIDE.md)
- [14 Prompt、Skills 与 MCP 指南](./14_PROMPT_SKILLS_AND_MCP_GUIDE.md)

## 外层控制模式

- [19 External Controller 指南](./19_EXTERNAL_CONTROLLER_GUIDE.md)
  说明如何基于 durable quest state、mailbox 和 `quest_control` 构建可选的外层治理控制器。

## Connector Runtime 指南

- [03 QQ 连接器指南](./03_QQ_CONNECTOR_GUIDE.md)
- [04 灵珠 / Rokid 指南](./04_LINGZHU_CONNECTOR_GUIDE.md)
- [10 微信连接器指南](./10_WEIXIN_CONNECTOR_GUIDE.md)
- [16 Telegram Connector 指南](./16_TELEGRAM_CONNECTOR_GUIDE.md)
- [17 WhatsApp Connector 指南](./17_WHATSAPP_CONNECTOR_GUIDE.md)
- [18 Feishu Connector 指南](./18_FEISHU_CONNECTOR_GUIDE.md)

## 作用边界说明

`docs/zh/` 是 upstream / user-facing guide corpus，面向用户和操作者流程。repo-specific MAS/MDS transition truth 放在 `docs/project.md`、`docs/architecture.md`、`docs/status.md`、`docs/policies/` 和 `docs/references/`。

这个仓库的职责更窄：

- 保留冻结源码与历史行为 fixture
- 支持显式 legacy restore/import/backend-audit diagnostic
- 通过受控 intake 记录有价值的上游改动
- 为 MAS-owned capability proof 提供 provenance、parity 和 no-history intake 参考

在架构上，`MedAutoScience` 是人类与 Agent 的主入口；MedDeepScientist（`med-deepscientist` 仓库）承担 archive/reference、legacy diagnostic 和可审计 upstream intake。它不是 OPL 当前 active domain agent，也不是 MAS 默认运行依赖；OPL 的 Codex-first、stage-led framework 只会把它作为 MAS 显式声明的 provenance、oracle 或 intake reference 消费。
