# MedDeepScientist 项目概览

## 项目是什么

`MedDeepScientist` 是 `MedAutoScience` 旧 MAS/MDS 分层后的 frozen source archive、historical fixture、explicit legacy diagnostic target 与 upstream intake reference。
当前它仍以受控 DeepScientist fork 的形态维护，但不再是 MAS 默认 runtime substrate，也不承担 MAS 默认 operation、diagnostic、progress、quality、artifact 或 WebUI 依赖。
它不是独立医学研究产品入口，也不持有 MAS 的研究设计、publication readiness、submission authority、runtime truth、artifact truth 或用户可见进度 owner。

## 项目目标

- 保存旧 MDS source、license/provenance、quest / daemon / durable workspace behavior fixture。
- 支持显式 legacy restore/import/backend-audit diagnostic。
- 在不污染 MAS default-branch contributor footprint 的前提下，为 MAS 后续 upstream intake 提供审计参考。

## 长线目标

- 保持 MDS repo 作为 archive/reference lane，而不是 MAS 默认运行 lane。
- 让 product entry、controller、policy、medical orchestration、runtime status、progress portal、artifact 和 quality surfaces 保持在 `MedAutoScience`。
- 让兼容壳在有证据的前提下逐步退役。
- 后续 upstream intake 只能通过 source ref/hash、capability classification、MAS owner、parity proof 和 no-history MAS-authored implementation 进入 MAS。

## 非目标

- 不做 upstream `DeepScientist` 的镜像同步分支。
- 不把 prompt/skill 体系重新改造成新的产品主入口。
- 不把 BenchStore、DeepXiv、UI/TUI、Hermes-native proof lane 或 upstream product docs 默认升级成 MAS-facing product contract。
- 不为了兼容旧入口放松已经明确的 runtime protocol。

## 默认入口

建议阅读顺序：

1. `README.md`
2. `docs/README.md`
3. `docs/status.md`
4. `docs/architecture.md`
5. `docs/invariants.md`
6. `docs/decisions.md`
7. `docs/policies/runtime_protocol.md`

## 代码主入口

- `src/deepscientist/`：runtime 主体
- `src/prompts/`：system prompt / continuation prompt 入口
- `src/skills/`：repo-tracked skill surface
- `tests/`：runtime、API、contract 与 compatibility regression
- `bin/ds.js`：薄启动层，不是主真相面
