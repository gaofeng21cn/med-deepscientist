# MedDeepScientist 文档总览

MedDeepScientist（`med-deepscientist` 仓库）是 `MedAutoScience` 依赖的受控 runtime fork。

这个仓库定位为一个目的清晰的半独立 runtime layer：它锁定一个已经验证的 baseline，并通过受控 intake 去吸收符合兼容契约的上游改动，从而避免每次 `DeepScientist` 的 prompt、skill、workflow 或 runtime 变动都变成医疗研究者的迁移负担。

这份文档索引面向 runtime 仓库本身。大多数医学用户应该从 `MedAutoScience` 进入；这个仓库主要用于说明：

- 为什么要 fork `DeepScientist`
- 这个 fork 保留了什么兼容性边界
- 上游 `DeepScientist` 更新应该怎样被安全吸收
- 当前继承下来的 runtime 行为应该去哪里查

当前仍保留这些兼容名字：

- Python package：`deepscientist`
- CLI：`ds`
- npm package：`@researai/deepscientist`

## 建议先看

- [稳定 Runtime Protocol](../policies/runtime_protocol.md)
  `MedAutoScience` 所依赖的最小稳定协议。
- [仓库 README](../../README.md)
  项目定位、fork 原因、架构关系与兼容策略。
- [Freeze Baseline](../medical_fork_baseline.md)
  受控 fork 的冻结基线和已吸收补丁记录。
- [上游 Intake 指南](../upstream_intake.md)
  如何把上游 `DeepScientist` 更新吸收到这个 fork。

## Runtime 维护

- [90 Architecture](../en/90_ARCHITECTURE.md)
  系统级约束与仓库结构。
- [91 Development](../en/91_DEVELOPMENT.md)
  面向维护者的开发与验证流程。
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

下面这些文档仍然描述了这个 fork 当前保留的底层 runtime 行为：

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

这个仓库不是新的医学 orchestration 产品。

它的职责更窄：

- 提供稳定、可审计的 runtime 执行层
- 为 `MedAutoScience` 降低上游兼容性漂移成本
- 通过受控 intake 吸收有价值的上游改动

在架构上，`MedAutoScience` 仍然是人类与 Agent 进入的主入口；MedDeepScientist（`med-deepscientist` 仓库）则是由 MedAutoScience 管理的 runtime 工程面，持续优化同时保持兼容。
