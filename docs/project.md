# MedDeepScientist 项目概览

## 项目是什么

`MedDeepScientist` 是面向 `MedAutoScience` 的稳定 runtime substrate。
当前它仍以受控 DeepScientist fork 的形态维护，同时承担 runtime contract 收敛、上游 intake 审计、以及 durable execution truth 维护。

## 项目目标

- 为 `MedAutoScience` 提供稳定的 quest / daemon / durable workspace runtime。
- 把 `MedAutoScience` 真实依赖的 runtime surface 压缩成清晰、可验证的最小协议。
- 在不破坏下游兼容性的前提下，持续吸收有价值的 upstream 变化。

## 长线目标

- 把 `MedDeepScientist` 收敛成 family 级稳定 runtime surface。
- 让 product entry、controller、policy 与 medical orchestration 继续上移到 `MedAutoScience`。
- 让兼容壳在有证据的前提下逐步退役。
- 让 repo 边界保持可演进：继续独立维护或后续吸收到 family mainline，取决于哪种形态更利于协议清晰和运维收口。

## 非目标

- 不做 upstream `DeepScientist` 的镜像同步分支。
- 不把 prompt/skill 体系重新改造成新的产品主入口。
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
