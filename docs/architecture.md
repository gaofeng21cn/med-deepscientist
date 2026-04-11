# MedDeepScientist 架构

## 主链路

`MedAutoScience` 通过稳定 runtime protocol 驱动 `MedDeepScientist`。
这里的关键链路不是“聊天应用 -> agent”，而是：

`controller / adapter -> daemon API -> quest runtime -> durable quest/worktree layout -> artifact surfaces`

## 核心模块

### 1. Runtime core

- `src/deepscientist/quest/`
- `src/deepscientist/artifact/`
- `src/deepscientist/daemon/`

这层负责 quest 生命周期、artifact durable surface、daemon API 和状态同步。

### 2. Prompt / skill surface

- `src/prompts/`
- `src/skills/`

这层负责 runtime 在长线自治执行中的 prompt 和 skill 语义，但其边界受 runtime protocol 和 quest durable layout 约束。

### 3. UI / packaging surface

- `src/ui/`
- `src/tui/`
- `bin/`

这层是宿主与发布形态，不是 runtime contract 的权威来源。

## 稳定边界

- 稳定协议以 `docs/policies/runtime_protocol.md` 为准。
- Quest 仍遵循“一题一仓”的 durable layout。
- `quest.yaml`、`brief.md`、`plan.md`、`status.md`、`SUMMARY.md` 属于稳定 durable surface。
- `MedAutoScience` 依赖的是协议与 durable surface，不是 prompt 细节或 UI 呈现细节。

## 文档分工

- 当前架构说明看本文件。
- 硬约束看 `docs/invariants.md`。
- 当前状态与活跃主线看 `docs/status.md`。
- 历史 intake / baseline 审计材料看 `docs/references/*`。
