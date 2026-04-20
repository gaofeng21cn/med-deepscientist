# MedDeepScientist 架构

## 主链路

`MedAutoScience` 通过稳定 runtime protocol 驱动 `MedDeepScientist`。
这里的关键链路不是“聊天应用 -> agent”，而是：

`controller / adapter -> daemon API -> quest runtime -> durable quest/worktree layout -> artifact surfaces`

在当前默认执行器口径下，这条链路在真正落到 AI 时还会继续细化为：

`controller / adapter -> daemon API -> RunRequest -> CodexRunner -> codex exec autonomous agent loop`

## 核心模块

### 1. Runtime core

- `src/deepscientist/quest/`
- `src/deepscientist/artifact/`
- `src/deepscientist/daemon/`

这层负责 quest 生命周期、artifact durable surface、daemon API、runner dispatch 和状态同步。

### 2. Runner / executor surface

- `src/deepscientist/runners/`
- `src/deepscientist/config/`

这层负责把 daemon / quest 运行请求路由到具体执行器。
当前默认执行器是 `CodexRunner`：

- `src/deepscientist/config/models.py::default_runners()` 默认写成 `model = "inherit"`、`model_reasoning_effort = ""`
- `src/deepscientist/runners/codex.py::CodexRunner._build_command()` 会只在显式 override 时追加 `--model` 或 reasoning 参数
- 因此 repo-tracked 默认语义是“继承本机 Codex 默认配置”，而不是仓内固定 `gpt-5.4 / xhigh`

当前还挂了一条同 contract 的 opt-in proof lane：

- `src/deepscientist/runners/hermes_native_proof.py::HermesNativeProofRunner`
- 选择方式是显式 `executor_kind = hermes_native_proof`
- 真实执行入口是 `run_agent.AIAgent.run_conversation`
- 该 lane 只用于证明 `Hermes-native` full agent loop contract 已可接入，不等价于默认执行器替换

### 3. Prompt / skill surface

- `src/prompts/`
- `src/skills/`

这层负责 runtime 在长线自治执行中的 prompt 和 skill 语义，但其边界受 runtime protocol 和 quest durable layout 约束。

### 4. UI / packaging surface

- `src/ui/`
- `src/tui/`
- `bin/`

这层是宿主与发布形态，不是 runtime contract 的权威来源。

### 5. Read-only catalog surface

- `src/deepscientist/benchstore/`

这层当前只承载只读 BenchStore registry surface：

- catalog entry schema 正常化
- catalog 列出 / 单项读取
- 基于核心字段的基础筛选与查询
- 基于 catalog entry 生成 setup packet
- 维护者 authoring / packaging 说明见 `docs/en|zh/22_BENCHSTORE_YAML_REFERENCE.md` 与 `docs/en|zh/23_BENCHSTORE_GITHUB_RELEASES_SPEC.md`

当前明确停在只读 contract，不扩到 `BenchStoreDialog`、`start_setup_patch`、setup quest 状态链或其他产品级 setup UI。

## 稳定边界

- 稳定协议以 `docs/policies/runtime_protocol.md` 为准。
- Quest 仍遵循“一题一仓”的 durable layout。
- `quest.yaml`、`brief.md`、`plan.md`、`status.md`、`SUMMARY.md` 属于稳定 durable surface。
- `MedAutoScience` 依赖的是协议与 durable surface，不是 prompt 细节或 UI 呈现细节。
- 当前最底层 AI 调用装配面是 `CodexRunner._build_command()`，不是 daemon API body 里的 repo-local 模型 pin。
- 默认 `model = "inherit"` 与空的 `model_reasoning_effort` 表示跟随本机 `Codex` 默认配置；只有显式 override 才会改变这一点。
- opt-in `Hermes-native` lane 也遵循相同原则：默认读取本机 `Hermes` 配置，不在 repo 内 pin model / reasoning。
- `executor_kind` 是稳定的 executor-adapter 选择面；默认值仍是 `codex_cli`，`hermes_native_proof` 只能显式请求。

## 文档分工

- 当前架构说明看本文件。
- 硬约束看 `docs/invariants.md`。
- 当前状态与活跃主线看 `docs/status.md`。
- 历史 intake / baseline 审计材料看 `docs/references/*`。
