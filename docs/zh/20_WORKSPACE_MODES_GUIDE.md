# 20 Workspace Modes 指南

MedDeepScientist 继续把 `Autonomous` 和 `Copilot` 当作用户侧 checkpoint autonomy 词汇，同时把 runtime 持久化真相保留在本地 `control_mode + continuation_policy` 合同上。

## 为什么需要这篇文档

最近一波 upstream 让 `workspace_mode` 更靠近 runtime control field。当前 fork 早已把 `workspace_mode` 用作 research/worktree 状态命名空间。直接按字段级吸收会把两套 authority 压进同一个持久化字段，所以当前安全路径是语义对齐，而不是复用存储字段。

## 本地合同

| Surface | Owner | Meaning |
| --- | --- | --- |
| `Autonomous` / `Copilot` 标签 | product、prompt、docs | 面向用户的 checkpoint autonomy 词汇 |
| `startup_contract.control_mode` | startup contract | 启动时的 checkpoint autonomy 选择 |
| `continuation_policy` / `continuation_reason` / `continuation_anchor` | runtime | startup、resume、recovery、external-progress reconcile 之后的当前 continuation truth |
| `workspace_mode` | research/worktree state | `quest`、`idea`、`analysis`、`paper`、`run`、`start_setup` 这类研究阶段与布局命名空间 |

## 语义映射

### 启动节奏

- `Autonomous` 映射到 `startup_contract.control_mode = autonomous`。
- `Copilot` 映射到 `startup_contract.control_mode = copilot`。
- 两种模式都可以立即启动第一个有边界的任务，差异出现在普通安全 checkpoint 之后。

### 续跑节奏

- `control_mode = autonomous` 表示普通续跑默认落到 `continuation_policy = auto`。
- `control_mode = copilot` 表示普通续跑默认落到 `continuation_policy = wait_for_user_or_resume`。
- 显式等待原因、恢复态、supervisor ownership、non-retryable error 继续由 runtime-owned continuation 字段表达，并可覆盖启动默认值。
- 排队中的用户消息始终优先于后台续跑。
- 当 `continuation_anchor` 已记录时，`/resume` 应从该 anchor 继续，而不是临时猜一个新 stage。

### 后台巡检节奏

- detach 的长任务继续使用 progress-first 巡检，标准 cadence 为 `60s -> 120s -> 300s -> 600s -> 1800s ...`。
- 在 `copilot` 下，前台 quest 可以保持待命给人审阅，后台巡检继续承担可见性和恢复判断。
- 在 `autonomous` 下，只要没有显式阻塞或审批边界，健康巡检结果可以自然衔接到下一步安全动作。
- 一旦进入 managed supervision 或 external controller ownership，本地 watch loop 应在记录并汇报 checkpoint 后让出控制权。

## 操作性理解

### `Autonomous`

当 quest 需要跨普通安全 checkpoint 持续推进时，用这组词。

本地落点：

- startup control：`control_mode = autonomous`
- default continuation：`auto`
- user gate：只有真实阻塞、显式审批边界或更强 continuation rule 才会让 quest 停下来

### `Copilot`

当 quest 需要在每个有边界的安全工作单元后把控制权交回给人时，用这组词。

本地落点：

- startup control：`control_mode = copilot`
- default continuation：`wait_for_user_or_resume`
- user gate：checkpoint 审阅是默认交接点，同时允许后台继续低频巡检

## 不变量

- `workspace_mode` 只承载 research/worktree 语义。
- checkpoint autonomy 继续放在 `startup_contract.control_mode`。
- runtime continuation truth 继续放在 `continuation_policy`、`continuation_reason` 与 `continuation_anchor`。
- 文案、prompt、docs 可以吸收 upstream 语义，runtime persistence 继续保持当前 fork 的本地合同。
