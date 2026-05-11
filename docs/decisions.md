# MedDeepScientist 关键决策

## 2026-05-11

### 决策：MDS 对 OPL 新定位保持 archive/reference 边界

- `OPL` 当前按 Codex-first、stage-led 的完整智能体运行框架理解，可作为外部依赖托管 active domain agent；`Codex CLI` 是 stage attempt 的最小执行单元。
- `MedDeepScientist` 不进入 OPL active domain agent、默认安装依赖、stage adapter 或 default runtime provider 列表。
- MAS 可以显式把 MDS 作为 backend audit、source provenance、historical fixture、explicit archive import、upstream intake 或 parity oracle reference；这不产生 MAS 默认 runtime dependency，也不产生新的医学研究 product entry。

## 2026-05-08

### 决策：MedDeepScientist 退为 MAS functional monolith 的 archive/reference lane

- `med-autoscience` 已关闭 functional monolith campaign。MAS 默认运行、诊断、进度可视化、artifact/quality/status/progress/cockpit、Progress Portal 与 OPL handoff 不再要求本仓 checkout、daemon、runtime root 或 WebUI。
- 本仓后续只保留 frozen source archive、historical fixture、explicit legacy restore/import/backend-audit diagnostic target 与 upstream intake reference 角色。
- 未来从本仓或 upstream DeepScientist 学习能力，必须在 MAS 侧以 source ref/hash、capability classification、MAS owner、authority boundary、parity proof、tests 和 no-history contributor audit 收口；不得把上游 history 或 contributor footprint 带入 `med-autoscience` default branch。

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
