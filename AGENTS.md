# MedDeepScientist 仓库协作规范

## 适用范围

本文件适用于仓库根目录及其所有子目录；若更深层目录存在 `AGENTS.md`，以更近者为准。

## 项目定位

- `MedDeepScientist` 是服务 `MedAutoScience` 的受控 `DeepScientist` runtime 分支，不是一个独立扩张的平台。
- 权威 runtime 仍在 `src/deepscientist/`，`bin/ds.js` 只是薄启动层。
- 这里的主目标是把 runtime 边界压窄、压稳、压清楚，而不是无条件追上 upstream 的所有变化。

## 非目标

- 不把仓库做成 upstream `DeepScientist` 的镜像同步分支。
- 不把 prompt/skill 工作流重新写回中心化大调度器。
- 不为了兼容旧入口而放松当前稳定 runtime protocol。

## 开发优先级

- 第一优先级：持续提升 `MedAutoScience -> MedDeepScientist` 兼容性，收紧 adapter 依赖。
- 第二优先级：减少隐式布局假设、重复 runtime 解释和无必要的兼容壳。
- 第三优先级：只吸收对当前 runtime 真正有价值的 upstream 变更。

## 主要入口与真相面

- 默认人类/AI 入口：`README.md`、`docs/README.md`、`docs/en/README.md`、`docs/zh/README.md`
- 稳定规则入口：`docs/policies/runtime_protocol.md`
- 核心实现入口：`src/deepscientist/`、`src/prompts/`、`src/skills/`、`tests/`
- Quest 仍遵循“一题一仓”的 durable layout；涉及 quest layout、daemon API、MCP built-ins 的修改，必须同步更新实现、文档和测试。

## 文档规则

- `README*` 与 `docs/README*` 是默认公开入口。
- `docs/en/` 与 `docs/zh/` 承担公开用户文档；`docs/policies/` 承担稳定规则文档。
- 公开用户文档保持中英双语；内部技术、规划与维护记录默认中文。
- 内部规划与 AI 过程文档放在本地未跟踪的 `docs/superpowers/`，不要放回 repo-tracked `docs/`。
- OMX 已退场；仓库中的 OMX 提示或说明只能作为历史背景，不能再被写成当前活跃入口。

## 变更与验证

- 保持 diff 小、可审查、可回退。
- 能删就别加；能复用现有模式就别新起抽象。
- 不要新增依赖，除非当前任务有明确、可验证的必要性。
- 只要改动 daemon API、quest layout、built-in MCP surface、prompt/skill 名单，就必须同步改测试和相关文档。
- 默认测试入口是 `uv run pytest`；涉及发布/打包改动时，额外运行 `npm run build:release` 与 `npm pack --dry-run`。
- 完成前必须运行与改动匹配的测试、类型检查和验证命令。

## 并行开发与工作树

- 大改动、长链路工作、并行多 AI 开发，默认先从当前 `main` 开独立 worktree，再在 worktree 内实现和验证。
- 共享根 checkout 只用于轻量阅读、评审、吸收验证后提交、push 和清理，不应长期承担重型实现。
- 若需要多条并行 lane，就创建多个 worktree，不要把多条长线塞进同一工作目录。

## 本地状态

- `.codex/` 是本地 Codex 工具状态，必须保持未跟踪。
- `.omx/` 只允许作为历史残留存在，必须保持未跟踪，且不得再作为当前 workflow 入口。
