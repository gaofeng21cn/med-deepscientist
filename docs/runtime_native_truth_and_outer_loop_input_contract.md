# Runtime Native Truth 与 Outer-Loop Input Contract

## 1. 目标

本文件冻结 `MedDeepScientist` 在 P0 阶段必须原生提供的 quest-owned runtime truth：

- runtime 不再只写 `.ds/runtime_state.json`
- 关键状态迁移必须同时物化成 durable `runtime_event`
- `MedAutoScience` 外环读取 runtime 输入时，不应再只能从多份 projection 反推

这里的重点不是 controller 再包一层，而是 runtime core 自己写出可审计、可复读、可被 transport 直接搬运的真相面。

## 2. Quest-Owned Native Runtime Event

### 2.1 Durable surface

每个 quest 的 native runtime event 固定写到：

- `artifacts/reports/runtime_events/<timestamp>_<event_kind>.json`
- `artifacts/reports/runtime_events/latest.json`

同时 `.ds/events.jsonl` 允许追加一个 `quest.runtime_event` pointer event，用来把 durable artifact 接到现有 append-only event stream 上。

### 2.2 Event schema

每条 native runtime event 至少包含：

- `schema_version`
- `event_id`
- `quest_id`
- `emitted_at`
- `event_source`
- `event_kind`
- `summary_ref`
- `status_snapshot`
- `outer_loop_input`

可选但当前实现已提供：

- `transition`
- `artifact_path`
- `summary`

### 2.3 Status snapshot / outer-loop input

`status_snapshot` 与 `outer_loop_input` 当前冻结的最小字段集相同：

- `quest_status`
- `display_status`
- `active_run_id`
- `runtime_liveness_status`
- `worker_running`
- `stop_reason`
- `continuation_policy`
- `continuation_anchor`
- `continuation_reason`
- `pending_user_message_count`
- `interaction_action`
- `interaction_requires_user_input`
- `active_interaction_id`
- `last_transition_at`

语义要求：

- `quest_status` 表示 runtime 语义状态，不允许把 `waiting_for_user / paused / stopped` 抹平。
- `display_status` 保留 `error` 这类对外显示语义，不要求等于 `quest_status`。
- `runtime_liveness_status` 至少区分：
  - `live`
  - `stale`
  - `none`
- `continuation_policy` 继续是 runtime-owned 调度字段；默认值可由 `startup_contract.control_mode` 推导，但一旦进入显式 wait / external-progress / none 等状态，仍以 runtime 当前值为准。
- `interaction_requires_user_input=true` 时，outer loop 不得继续把 quest 叙述成“稳定托管自动推进中”。

## 3. Event emission rules

P0 需要覆盖以下原生迁移：

- turn start
- `running -> waiting_for_user`
- `running -> paused`
- `running -> stopped`
- stale active run reconcile
- runner postprocess error / degraded display state
- auto resume suppression

这些场景都必须留下 native runtime event；不能只留下 `.ds/runtime_state.json` 的最终值。

## 4. Session / transport exposure

`GET /api/quests/{quest_id}/session` 在最小 stable contract 之外，新增 native truth 扩展：

- `runtime_event_ref`
- `runtime_event`

要求：

- 若二者同时存在，必须指向同一个 durable artifact
- transport 可直接把这一对字段向上传递给 `MedAutoScience`
- ACP/UI 兼容层不要求把 `quest.runtime_event` 强制塞成最后一条普通用户事件，但 raw event plane 必须保留

## 5. 与 MedAutoScience outer loop 的关系

`MedDeepScientist` 的 native event 不负责直接生成 study-owned controller 决策，也不负责伪装成：

- `runtime_watch`
- `controller_decisions/latest.json`
- `runtime_escalation_record.json`

它只负责把 quest-owned runtime 真相先稳定写出来。  
`MedAutoScience` outer loop 后续应当以 native event 为输入，再做 study-owned 决策与监管产物。

## 6. Fail-closed 要求

- 没有 native runtime event 时，transport/outer loop 不得假定“没有异常”。
- `latest.json` 缺失、schema 非法、quest_id 不匹配时，必须报错。
- 不允许再用 controller 侧推断把 `stale / waiting / paused / stopped / degraded` 静默折叠回 `active + healthy`。
