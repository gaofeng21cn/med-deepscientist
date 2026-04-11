# MedDeepScientist 项目概览

## 项目是什么

`MedDeepScientist` 是服务 `MedAutoScience` 的受控 runtime 分支。
它保留 `DeepScientist` 的长线自治执行能力，但把默认工程目标从“快速扩张产品能力”改成“稳定、可审计、可验证的 runtime 合同”。

## 项目目标

- 为 `MedAutoScience` 提供稳定的 quest / daemon / durable workspace runtime。
- 把 `MedAutoScience` 真实依赖的 runtime surface 压缩成清晰、可验证的最小协议。
- 在不破坏下游兼容性的前提下，持续吸收有价值的 upstream 变化。

## 非目标

- 不做 upstream `DeepScientist` 的镜像同步分支。
- 不把 prompt/skill 体系重新改造成中心化大调度器。
- 不为了兼容旧入口放松已经冻结的 runtime protocol。

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
