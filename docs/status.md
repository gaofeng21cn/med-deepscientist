# MedDeepScientist 当前状态

## 当前定位

- 仓库角色：`MedAutoScience` 的稳定 runtime substrate，当前通过受控 fork 形态维护
- MAS/MDS 迁移收缩角色：`controlled backend`、`behavior oracle`、`upstream intake buffer`
- 论文质量边界：MDS `paper_contract_health` 是 `backend_preflight`，coverage 是 `mechanical_oracle`；existing draft、coverage complete、contract ok 不能越权成为 MAS medical manuscript quality ready
- 当前开发口径：收紧 runtime protocol、收窄 adapter 依赖、谨慎吸收 upstream
- 长线方向：把 runtime surface 收敛成 family 级稳定合同，repo 边界保持可演进
- 当前执行真相：最底层 AI 执行继续通过 `CodexRunner -> codex exec autonomous agent loop` 落地；默认 `model / reasoning` 继承本机 `Codex` 默认配置，而不是 repo-local pin 固定型号
- 当前 opt-in proof lane：显式 `executor_kind = hermes_native_proof` 时，可路由到 `HermesNativeProofRunner -> run_agent.AIAgent.run_conversation`；它只接受真实 full agent loop proof，不接受 chat-only relay
- 当前 `claude` / `opencode` 只保留为 reserved experimental runner ids；当前 release 只维护 config / doc / test contract，不开放真实 runner 产品面
- OMX 状态：已退场，仅允许历史残留

## 当前主线

- 稳定协议入口：`docs/policies/runtime_protocol.md`
- 迁移收缩契约：`docs/policies/mas_mds_transition_contract.md`
- 核心工作方式入口：根 `AGENTS.md`
- 当前文档骨架：`project / architecture / invariants / decisions / status`
- BenchStore 已开放 `catalog -> setup packet -> Start Research / SetupAgent` 的受控入口；`start_setup_patch` 回写与 setup assist 验证已经落到当前主线
- BenchStore maintainer docs 已补齐 YAML authoring 与 GitHub Releases packaging contract，文档口径继续停在当前 fork 的 read-only catalog + setup packet 边界
- DeepXiv authoring 继续停留在 Settings surface；当前支持 `base_url`、直接 token、`token_env` env-only lookup，不挂进 Start Research

## 当前执行链

- `MedAutoScience` 通过稳定 runtime protocol 驱动 `MedDeepScientist`
- `src/deepscientist/daemon/api/handlers.py` 会构造 `RunRequest`
- 默认 runner 是 `src/deepscientist/runners/codex.py::CodexRunner`
- `CodexRunner._build_command()` 负责组装真实的 `codex exec` 命令
- 当前默认 runner 配置来自 `src/deepscientist/config/models.py::default_runners()`：
  - `model = "inherit"`
  - `model_reasoning_effort = ""`
  - 只有显式 override 才会把 `--model` 或 reasoning effort 传给 CLI
  - `claude` / `opencode` 保留 disabled metadata slot，用来承载 reserved experimental contract

这意味着本仓当前并不是“自己直接打一发 chat completion”，而是把任务交给本机 `Codex` 的 autonomous agent loop 去执行。

当前新增的 `Hermes-native` 入口只是 experimental opt-in proof lane：

- 默认 runner / executor 不变，仍是 `codex` / `codex_cli`
- 只有显式请求 `executor_kind = hermes_native_proof` 时才会走 Hermes proof runner
- proof runner 默认继承本机 `~/.hermes/config.yaml` 的 model / provider / api_mode / reasoning
- 允许用 `DEEPSCIENTIST_HERMES_*` 环境变量显式 override
- 只要没有工具事件、没有完成 full agent loop、或 final response 不是合法 object，就必须 fail-closed
- `Copilot / Autonomous` 这组用户侧命名继续映射到 `startup_contract.control_mode`：`autonomous` 表示普通安全 checkpoint 默认继续推进，`copilot` 表示完成当前安全工作单元后转入人工审阅待命
- `continuation_policy` 与 `continuation_reason` 继续由 runtime 持有，并在 quest create、startup-context switch、resume/recovery、external-progress reconcile 时做一致化收敛
- `workspace_mode` 继续保留为 research/worktree 命名空间，承载 `quest | idea | analysis | paper | run | start_setup` 这类阶段或布局语义，不承担 checkpoint autonomy 控制权
- 后台长任务继续使用 progress-first 巡检节奏 `60s -> 120s -> 300s -> 600s -> 1800s ...`；`copilot` 允许前台待命同时低频巡检，`autonomous` 允许在无显式阻塞时基于巡检结果继续下一步
- MiniMax / GLM / Ark / Bailian 继续走 Codex profile path；provider env sanitization 与 chat-wire tool guard 都属于 Codex compatibility lane

## 当前优先事项

1. 保持 `MedAutoScience -> MedDeepScientist` 兼容性清晰且可验证。
2. 按 `controlled backend / behavior oracle / upstream intake buffer` 收缩 MDS 角色，避免把 MDS 扩成第二个 MAS product owner。
3. 保持 paper health / coverage / prompt skill 只消费结构化 authority 字段；MAS AI preflight、prose review、publication_eval 才能驱动医学论文质量 readiness。
4. 减少 quest layout、prompt/skill、daemon API 上的隐式耦合。
5. 保持根级 docs、公开用户文档与真实执行链同步，不把 repo-local 模型 pin 写回 family 默认 truth。
6. 让 upstream intake 继续通过审计与验证推进，只吸收能强化 runtime contract、parity oracle 或兼容性证明的变化。
7. 让 README、docs index、status/project 文档对齐“runtime substrate + 协议收敛 + 可演进 repo 边界”的当前定位。

## 默认验证

- 默认最小验证：`scripts/verify.sh`
- full 验证：`scripts/verify.sh full`
- 发布相关改动：`scripts/verify.sh release`

## 补充材料

- 上游 intake 说明：`docs/upstream_intake.md`
- workspace-mode / continuation 语义说明：`docs/zh/20_WORKSPACE_MODES_GUIDE.md`、`docs/en/20_WORKSPACE_MODES_GUIDE.md`
- 五个核心 skill owner split 参考：`docs/references/upstream_skill_owner_split_2026_04_20.md`
- baseline / 审计说明：`docs/medical_fork_baseline.md`
- 公开用户文档：`docs/en/`、`docs/zh/`
