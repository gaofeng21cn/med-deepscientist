# MedDeepScientist 仓库协作规范

## 适用范围

本文件适用于仓库根目录及其所有子目录；若更深层目录存在 `AGENTS.md`，以更近者为准。

## 定位

- `AGENTS.md` 只约束工作方式，不承载项目知识细节。
- 项目知识默认从 `README.md`、`docs/README.md`、`docs/project.md`、`docs/status.md`、`docs/architecture.md`、`docs/invariants.md`、`docs/decisions.md` 读取。
- `MedDeepScientist` 是服务 `MedAutoScience` 的受控 runtime 分支；目标是稳定 runtime 协议与边界，而不是追逐 upstream 同步速度。

## 开发原则

- 第一优先级：压实 `MedAutoScience -> MedDeepScientist` runtime compatibility contract。
- 第二优先级：减少隐式布局假设、重复解释和无必要兼容壳。
- 第三优先级：只吸收对当前 runtime 真正有价值、可验证的 upstream 变化。
- 不做降级处理、兜底补丁、启发式修补或“先糊住再说”式实现。

## 文档体系

- `README*` 与 `docs/README*` 是默认人类/AI 入口。
- `docs/project.md`：项目概览与目标。
- `docs/architecture.md`：模块边界、主链路与实现结构。
- `docs/invariants.md`：硬约束与不能破坏的边界。
- `docs/decisions.md`：仍有效的关键决策与取舍。
- `docs/status.md`：当前状态、活跃主线、下一步和验证口径。
- `docs/policies/`：稳定、长期保留的规则文档。
- `docs/en/` 与 `docs/zh/`：公开用户文档。
- `docs/references/`：repo-tracked 参考材料、审计材料、上游 intake 记录。
- `docs/history/`：历史归档与退役材料，不作为当前活跃入口。
- `docs/superpowers/`：本地 AI 过程文档，必须保持未跟踪。

## 文档规则

- 公开用户文档保持中英双语；内部技术、维护与规划文档默认中文。
- 新文档先判断角色，再决定落点；不允许把参考材料、历史记录、当前状态和稳定规则混在同一层。
- 如果某条规则已经稳定并需要长期遵守，应写入 `docs/invariants.md` 或 `docs/policies/*`，不要继续堆在 `AGENTS.md`。

## 变更与验证

- 保持 diff 小、可审查、可回退。
- 能删就别加；能复用现有模式就别新起抽象。
- 没有明确、可验证的必要性，不要新增依赖。
- 只要改动 daemon API、quest layout、built-in MCP surface、prompt/skill 名单，就必须同步更新实现、测试与相关文档。
- 叙述性 `README*`、`docs/**` 和参考文档不作为脚本/测试的断言对象；可以测试 machine-readable contract、schema、CLI/API 行为、生成产物结构与路径，但不要用测试固定文档措辞、章节或状态文案。
- 默认最小验证入口是 `scripts/verify.sh`；默认 smoke lane 运行 `uv run pytest` 的契约切片。
- 涉及发布/打包改动时，额外运行 `npm run build:release` 与 `npm pack --dry-run`。
- 完成前必须运行与改动匹配的测试、类型检查和验证命令。

## 并行开发与工作树

- 大改动、长链路工作、并行多 AI 开发，默认先基于最新 `main` 开独立 worktree，再在 worktree 内实现和验证。
- 共享根 checkout 只用于轻量阅读、评审、吸收验证后提交、push 和清理，不应长期承担重型实现。
- 若需要多条并行 lane，就创建多个 worktree，不要把多条长线塞进同一工作目录。
- worktree 内实现和验证完成后，应尽快吸收回 `main`，并清理对应 worktree、分支与临时状态。

## 本地状态

- `.codex/` 是本地 Codex 工具状态，必须保持未跟踪。
