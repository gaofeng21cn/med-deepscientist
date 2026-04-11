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
6. [最小稳定 runtime protocol](policies/runtime_protocol.md)
7. [English docs index](en/README.md)
8. [中文文档索引](zh/README.md)

## 文档角色

### 核心文档

- [project.md](project.md)
- [architecture.md](architecture.md)
- [invariants.md](invariants.md)
- [decisions.md](decisions.md)
- [status.md](status.md)

### 稳定规则

- [policies/runtime_protocol.md](policies/runtime_protocol.md)

### 公开用户文档

- [docs/en/README.md](en/README.md)
- [docs/zh/README.md](zh/README.md)

### 参考 / 审计材料

- [upstream_intake.md](upstream_intake.md)
- [upstream_intake_round_2026_04_01.md](upstream_intake_round_2026_04_01.md)
- [medical_fork_baseline.md](medical_fork_baseline.md)

## 开发入口

- 最小验证入口：`scripts/verify.sh`
- full 验证：`scripts/verify.sh full`
- release 验证：`scripts/verify.sh release`

## 文档边界

- `README*` 与 `docs/README*`：默认入口
- `docs/project.md` / `architecture.md` / `invariants.md` / `decisions.md` / `status.md`：AI 和维护者的核心知识入口
- `docs/policies/`：稳定规则
- `docs/en/` 与 `docs/zh/`：公开用户文档
- `docs/superpowers/`：本地 AI 过程文档，必须保持未跟踪
