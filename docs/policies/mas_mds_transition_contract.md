# MAS/MDS 迁移收缩契约

Status: `active contract`  
Applies to: `MedAutoScience -> MedDeepScientist` transition boundary  
Authority: `docs/policies/runtime_protocol.md`

## 1. 角色收缩

`MedDeepScientist` 在 MAS 单项目演进线中的当前角色收缩为三类后端责任：

- controlled backend：只通过稳定 daemon API、quest durable layout、startup/turn contract 与 native runtime event surface 被 `MedAutoScience` 调用。
- behavior oracle：保留 quest 生命周期、branch/worktree、artifact、memory、runtime liveness 与 runner dispatch 的可回归行为，作为 MAS 吸收能力时的 parity oracle。
- upstream intake buffer：审计 upstream DeepScientist 变化，把确实增强 MAS runtime contract 的改动吸收到 MDS；其余变化保持在 intake 记录或 oracle 参考层。

这些角色不产生新的产品入口，也不把医学研究 owner 权限迁回 MDS。

## 2. MAS owner 必须消费的 surface

MAS owner 只能把以下 MDS surface 当作默认可消费合同：

- `docs/policies/runtime_protocol.md` 明确列出的 daemon routes、request/response minimum keys、quest/worktree layout、startup contract、turn contract 与 native runtime event surface。
- `quest.yaml`、`brief.md`、`plan.md`、`status.md`、`SUMMARY.md` 及 runtime protocol 列出的稳定 runtime directories。
- `startup_contract` 的 runtime-owned stable subset 与 controller-owned extension roundtrip 语义。
- `runtime_audit`、`runtime_event_ref`、`runtime_event`、`events`、`workflow` 等已列入 runtime protocol 的 runtime truth surface。
- `executor_kind` 与 runner lane 的稳定选择语义，其中默认执行器继续是 `codex_cli` / `codex`，`hermes_native_proof` 只作为显式 opt-in proof lane。

MAS 的 product entry、medical controller、profile、overlay、study intake、publication gate、submission package、journal/reviewer policy、医学证据解释与用户可见进度口径，继续由 MAS owner 承接。

## 3. 只作为 MDS parity/oracle 的 surface

以下内容可用于 MAS 做 parity 对照、回归 oracle 或 upstream intake 评估，但不能被 MAS owner 默认消费为产品合同：

- prompt prose、stage skill 内部流程、skill wording、非稳定 Turn Driver 之外的提示词细节。
- UI/TUI rendering payload、connector-specific transport 细节、可选 `/api/v1/*` 产品 API、annotation/latex/admin surface。
- BenchStore、DeepXiv、Hermes-native proof、reserved experimental runner ids 等尚未写入 runtime protocol 的产品或实验 lane。
- upstream DeepScientist 新增能力在经过 MDS intake、runtime contract promotion 与 targeted regression 之前的任何行为。

如果 MAS 需要把上述任一 surface 变成 owner-consumable contract，必须先把它提升到 `docs/policies/runtime_protocol.md`，并在同一变更中补齐测试。

## 4. 明确非目标

- No physical migration：本契约只收缩 runtime boundary，不移动仓库、不搬迁源码、不执行 monorepo absorb。
- No new product entry：MDS 不新增 MAS-facing 产品入口，不暴露新的默认 CLI/UI/frontdesk。
- No ownership inversion：医学研究设计、证据规则、publication readiness 与 submission authority 不从 MAS 下沉到 MDS。
- No silent surface widening：未写入 runtime protocol 的 MDS 行为不得被下游当成稳定 adapter contract。

## 5. Strangler 收缩阶梯

MDS surface 的后续演进只能沿以下阶梯移动，不能跳级：

1. `retain_in_mds_backend`：继续作为 backend 内部实现存在，只服务 daemon、runner、quest layout 或 artifact/memory 行为。
2. `oracle_only`：允许 MAS 用来做 parity 对照、回归定位或 upstream intake 评估，但不能被 MAS product entry、医学质量 gate 或用户进度面直接消费。
3. `promote_to_runtime_protocol`：只有当 MAS 确实需要稳定消费该 surface 时，先写入 `docs/policies/runtime_protocol.md`，并在同一变更中补 targeted regression。
4. `mas_owned_or_absorbed`：当该 surface 已经承载医学研究 owner 语义、publication readiness、submission authority 或用户可见研究进度，默认应迁到 MAS owner 面；MDS 只保留兼容 shim 或 oracle fixture。

判定规则：

- 只要 surface 回答“医学论文该不该继续、质量是否闭环、投稿包是否 ready”，它属于 MAS owner 面。
- 只要 surface 回答“quest 是否可运行、runner 如何启动、runtime event 如何回放、artifact/memory layout 是否兼容”，它可以留在 MDS backend/oracle 面。
- 任何跨越上述边界的变更都必须同时说明：当前 owner、目标 owner、promotion gate、parity proof 和 rollback surface。

## 6. 可验证门槛

迁移收缩相关变更至少满足以下条件：

1. `docs/status.md`、`docs/architecture.md` 与本契约保持同一角色表述。
2. `docs/policies/runtime_protocol.md` 明确引用本契约，并继续作为唯一稳定 runtime authority。
3. 任何 MAS-consumable surface 的新增或语义变化，都同步更新 runtime protocol 与 targeted regression tests。
4. 任何 upstream intake 只能在增强 runtime contract、behavior oracle 或兼容性证明时进入主线。
5. 任何 MDS surface promotion 都必须显式落到 `retain_in_mds_backend`、`oracle_only`、`promote_to_runtime_protocol` 或 `mas_owned_or_absorbed` 其中一个阶梯状态。
