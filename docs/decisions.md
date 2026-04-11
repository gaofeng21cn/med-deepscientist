# MedDeepScientist 关键决策

## 2026-04-11

### 决策：采用核心五件套文档骨架

- `docs/project.md`
- `docs/architecture.md`
- `docs/invariants.md`
- `docs/decisions.md`
- `docs/status.md`

原因：把项目知识从 `AGENTS.md` 与分散说明中收拢到固定入口，降低 AI 和维护者的检索成本。

### 决策：`AGENTS.md` 只保留工作方式

原因：项目知识经常变化，工作方式应稳定；把两者混写会导致规则和事实一起漂移。

### 决策：OMX 只保留历史语义

原因：OMX 已经退场。后续任何 OMX 相关提示若仍存在，只能作为历史背景，不再作为活跃入口或当前运行方式说明。

### 决策：统一最小验证入口

原因：AI 和维护者需要一个固定、低歧义的最小验证入口，因此新增 `scripts/verify.sh` 作为默认 smoke / full / release 调用面。
