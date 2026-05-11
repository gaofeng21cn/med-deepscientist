# MedDeepScientist Docs

这里是 `med-deepscientist` 的 docs 总入口。
文档管理的目标不是继续堆积材料，而是让维护者和 AI 能快速判断：

- 项目是什么
- 当前在哪
- 哪些边界不能动
- 哪些材料只是参考或历史

## 建议阅读顺序

1. [项目概览](project.md)
2. [当前状态](status.md)
3. [架构](architecture.md)
4. [硬约束](invariants.md)
5. [关键决策](decisions.md)
6. [MAS/MDS 迁移收缩契约](policies/mas_mds_transition_contract.md)
7. [Docs portfolio consolidation](docs_portfolio_consolidation.md)
8. [最小稳定 runtime protocol](policies/runtime_protocol.md)
9. [English docs index](en/README.md)
10. [中文文档索引](zh/README.md)
11. [Windows WSL2 deployment guide](en/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)
12. [Windows WSL2 部署指南](zh/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)

## 文档角色

### 核心文档

- [project.md](project.md)
- [architecture.md](architecture.md)
- [invariants.md](invariants.md)
- [decisions.md](decisions.md)
- [status.md](status.md)

### 稳定规则

- [policies/runtime_protocol.md](policies/runtime_protocol.md)
- [policies/mas_mds_transition_contract.md](policies/mas_mds_transition_contract.md)
- [policies/system_visibility_contract.md](policies/system_visibility_contract.md)

### 文档组合边界

- Active：核心五件套和当前 status，描述现在仍生效的项目事实、流程入口和执行边界。
- Policies：`docs/policies/`，只放长期稳定的 protocol、contract 与可复用治理规则，包括 native runtime truth / outer-loop input contract。
- References：`docs/references/`，放仍有当前参考价值的 upstream intake procedure、controlled-fork baseline 与 owner split 审计材料。
- History：`docs/history/`，放历史轮次记录、退役材料和不再作为当前入口的过程归档。
- Public user docs：`docs/en/` 与 `docs/zh/`，保持 upstream / user-facing guide corpus；repo-specific MAS/MDS transition truth 放在 core、policies 与 references。

## 当前边界提醒

`MedDeepScientist` 已不再是 `MedAutoScience` 的默认 runtime/backend 依赖。MAS functional monolith closeout 后，它只承担 frozen source archive、historical fixture、explicit legacy restore/import/backend-audit diagnostic 与 upstream intake reference 职责。它不是 OPL 默认 active domain agent、默认安装依赖或 stage adapter，也不是独立医学研究产品入口；OPL 的 Codex-first、stage-led framework 只会在 MAS 显式声明时把本仓作为 provenance、oracle 或 intake reference 消费。MAS 默认运行、诊断、进度、质量、artifact 和 Progress Portal 不应要求本仓 checkout、daemon、runtime root 或 WebUI。BenchStore、DeepXiv、UI/TUI、Hermes-native proof lane 和 upstream product docs 只能作为 fork-local capability、historical fixture、parity oracle 或 intake 参考；后续若要进入 MAS，必须通过 MAS 侧 source provenance、capability classification、parity proof、no-history author audit 和 MAS-owned implementation。

`README*` 与 `docs/**` 是人读面。运行时 report、测试、脚本和 dashboard 可以使用 `human_doc:*` 语义 ID 指向人类可读上下文，但不应把 `docs/**/*.md` 路径当作稳定机读 contract、promotion gate 或兼容性约束。

### 公开用户文档

- [docs/en/README.md](en/README.md)
- [docs/zh/README.md](zh/README.md)
- [docs/en/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md](en/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)
- [docs/zh/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md](zh/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md)

### 参考 / 审计材料

- [references/upstream_intake.md](references/upstream_intake.md)
- [references/medical_fork_baseline.md](references/medical_fork_baseline.md)
- [references/resource_source_truth_audit.md](references/resource_source_truth_audit.md)

### 文档治理

- [docs_portfolio_consolidation.md](docs_portfolio_consolidation.md)
- [policies/runtime_native_truth_and_outer_loop_input_contract.md](policies/runtime_native_truth_and_outer_loop_input_contract.md)

### 历史归档

- [history/README.md](history/README.md)
- [history/upstream-intake/README.md](history/upstream-intake/README.md)

## 开发入口

- 最小验证入口：`scripts/verify.sh`
- full 验证：`scripts/verify.sh full`
- release 验证：`scripts/verify.sh release`

## 文档边界

- `README*` 与 `docs/README*`：默认入口
- `docs/project.md` / `architecture.md` / `invariants.md` / `decisions.md` / `status.md`：AI 和维护者的核心知识入口
- `docs/policies/`：稳定规则
- `docs/en/` 与 `docs/zh/`：upstream / user-facing guide corpus
- `docs/references/`：仍可作为当前判断参考的审计与背景材料
- `docs/history/`：历史归档，不作为当前活跃入口
- 本地 AI / Superpowers 过程草稿默认保持未跟踪，必要时放入用户级 `~/.codex/` 归档，不作为 repo-tracked docs 层级
