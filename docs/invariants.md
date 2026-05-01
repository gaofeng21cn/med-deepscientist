# MedDeepScientist 硬约束

## Runtime 协议

- `docs/policies/runtime_protocol.md` 是 `MedAutoScience -> MedDeepScientist` 的稳定协议入口。
- 未被该协议显式列出的 surface，不得默认视为稳定 adapter contract。

## Quest durable surface

- Quest 继续采用“一题一仓”的 durable layout。
- `quest.yaml`、`brief.md`、`plan.md`、`status.md`、`SUMMARY.md` 是稳定 durable files。
- 任何改动 quest layout、daemon API、built-in MCP surface 的工作，都必须同步改实现、测试和文档。
- 大型 public dataset 默认只作为 accession / metadata / manifest 进入 durable state；没有明确 quest scope、具体分析用途、体积预算、复用位置与清理/保留策略时，不得下载或长期保留完整 MRI/GEO/SRA/FASTQ 等原始镜像。

## Upstream intake

- 不能盲目同步 upstream。
- 任何 upstream 吸收都必须通过可审计 intake 与回归验证。
- 与 `MedAutoScience` 兼容性无关、不能产生明确价值的 upstream 变化，不应进入主线。

## 文档治理

- `AGENTS.md` 只管工作方式，不堆项目事实。
- 项目事实优先收敛到 `docs/project.md`、`docs/architecture.md`、`docs/invariants.md`、`docs/decisions.md`、`docs/status.md`。
- 公开文档保持双语；内部技术与维护文档默认中文。

## 本地状态

- `.codex/` 必须保持未跟踪。
- `.omx/` 若存在，只能是历史残留，必须保持未跟踪，且不得再作为当前 workflow 入口。
