# MedDeepScientist 当前状态

## 当前定位

- 仓库角色：`MedAutoScience` 的受控 runtime 分支
- 当前开发口径：收紧 runtime protocol、收窄 adapter 依赖、谨慎吸收 upstream
- 当前执行真相：最底层 AI 执行继续通过 `CodexRunner -> codex exec autonomous agent loop` 落地；默认 `model / reasoning` 继承本机 `Codex` 默认配置，而不是 repo-local pin 固定型号
- 当前 opt-in proof lane：显式 `executor_kind = hermes_native_proof` 时，可路由到 `HermesNativeProofRunner -> run_agent.AIAgent.run_conversation`；它只接受真实 full agent loop proof，不接受 chat-only relay
- OMX 状态：已退场，仅允许历史残留

## 当前主线

- 稳定协议入口：`docs/policies/runtime_protocol.md`
- 核心工作方式入口：根 `AGENTS.md`
- 当前文档骨架：`project / architecture / invariants / decisions / status`
- BenchStore 当前只开放只读 registry/catalog surface；`BenchStoreDialog`、`start_setup_patch` 与 setup 状态链继续留在 scope 外

## 当前执行链

- `MedAutoScience` 通过稳定 runtime protocol 驱动 `MedDeepScientist`
- `src/deepscientist/daemon/api/handlers.py` 会构造 `RunRequest`
- 默认 runner 是 `src/deepscientist/runners/codex.py::CodexRunner`
- `CodexRunner._build_command()` 负责组装真实的 `codex exec` 命令
- 当前默认 runner 配置来自 `src/deepscientist/config/models.py::default_runners()`：
  - `model = "inherit"`
  - `model_reasoning_effort = ""`
  - 只有显式 override 才会把 `--model` 或 reasoning effort 传给 CLI

这意味着本仓当前并不是“自己直接打一发 chat completion”，而是把任务交给本机 `Codex` 的 autonomous agent loop 去执行。

当前新增的 `Hermes-native` 入口只是 experimental opt-in proof lane：

- 默认 runner / executor 不变，仍是 `codex` / `codex_cli`
- 只有显式请求 `executor_kind = hermes_native_proof` 时才会走 Hermes proof runner
- proof runner 默认继承本机 `~/.hermes/config.yaml` 的 model / provider / api_mode / reasoning
- 允许用 `DEEPSCIENTIST_HERMES_*` 环境变量显式 override
- 只要没有工具事件、没有完成 full agent loop、或 final response 不是合法 object，就必须 fail-closed

## 当前优先事项

1. 保持 `MedAutoScience -> MedDeepScientist` 兼容性清晰且可验证。
2. 减少 quest layout、prompt/skill、daemon API 上的隐式耦合。
3. 保持根级 docs、公开用户文档与真实执行链同步，不把 repo-local 模型 pin 写回 family 默认 truth。
4. 让 upstream intake 继续通过审计与验证推进，而不是零散吸收。

## 默认验证

- 默认最小验证：`scripts/verify.sh`
- full 验证：`scripts/verify.sh full`
- 发布相关改动：`scripts/verify.sh release`

## 补充材料

- 上游 intake 说明：`docs/upstream_intake.md`
- baseline / 审计说明：`docs/medical_fork_baseline.md`
- 公开用户文档：`docs/en/`、`docs/zh/`
