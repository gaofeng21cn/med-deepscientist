# Read-only System Visibility Contract

Status: `stable_internal`
Applies to: `/api/system/*` operator visibility slice

## Scope

当前仓库吸收的 system visibility 只提供只读观察面，用于让维护者、Settings surface、外部 operator 读取当前 runtime 状态。

这条线覆盖：

- runtime / quest 总览
- quest 列表与单 quest 摘要
- connector / bash / runtime session 可见性
- daemon / quest events / bash log source 与 tail
- failures 聚合
- runtime tools 状态
- host hardware 摘要
- chart catalog 与只读 chart query
- stats summary
- 关键字搜索

## Stable route family

- `GET /api/system/overview`
- `GET /api/system/quests`
- `GET /api/system/quests/:quest_id/summary`
- `GET /api/system/runtime/sessions`
- `GET /api/system/logs/sources`
- `GET /api/system/logs/:source_id/tail`
- `GET /api/system/failures`
- `GET /api/system/runtime-tools`
- `GET /api/system/hardware`
- `GET /api/system/charts`
- `GET /api/system/charts/:chart_id`
- `GET /api/system/stats/summary`
- `GET /api/system/search`

兼容 alias 只保留当前 Settings / admin bridge 已经引用的只读读面：

- `GET /api/admin/system/overview`
- `GET /api/admin/log-sources`
- `GET /api/admin/logs/:source_id/tail`

## Non-goals

当前 tranche 不吸收以下控制面：

- system shutdown / repair / controller run
- mutable task orchestration
- hardware preference write-back
- 独立 admin product surface

这条 contract 的目标是把 operator visibility 做成当前 fork 可依赖的只读面，而不是把 upstream admin center 整块搬进来。
