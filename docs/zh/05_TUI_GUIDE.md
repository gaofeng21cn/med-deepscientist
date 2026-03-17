# 05 TUI 使用指南：如何使用终端界面

这份文档是当前 DeepScientist TUI 的**单一权威使用说明**（以本仓库实现为准）。

如果你想了解更完整的运行时控制流、Prompt/Skill 执行模型、MCP 语义、以及 Canvas（Git 图）如何被重建，请同时阅读 `docs/zh/06_RUNTIME_AND_CANVAS.md`。

## 安装与启动

在当前仓库目录中：

```bash
uv sync
npm install
```

常用启动方式：

```bash
ds
ds --tui
ds --both
ds --status
ds --stop
```

说明：

- `ds`：启动守护进程，打印醒目的本地 Web 链接，尝试自动打开浏览器，然后退出。
- `ds --tui`：启动守护进程，并进入基于 Ink 的终端工作区。
- `ds --both`：同时打开 Web 工作区，并保持终端工作区附着运行。
- `ds --stop`：停止**守护进程本身**（不是仅停止某个 quest）。
- 仍可使用 `python -m deepscientist.cli ...` 做底层操作，但推荐通过 launcher 使用。
- 在源码仓库里，`node bin/ds.js` 与 `ds` 的行为一致

## TUI 内的核心操作

在 TUI 中：

- `/home`：回到“未绑定 quest”的请求模式。
- `/projects`：打开 quest 列表（浏览/切换）。
- `/use <quest_id>`：绑定当前 TUI 会话到指定 quest。
- `/new <goal>`：在 TUI 内创建新 quest。
- `/new <goal>` 会创建 quest，并通过守护进程自动启动首轮执行。
- `/delete <quest_id> --yes`：删除 quest（危险操作，需要确认）。
- 直接输入普通文本：发送到当前绑定的 quest（作为用户消息）。
- `/status`：查看当前 quest 状态。
- `/graph`：查看当前 quest 的 Git 图（分支与研究过程）。
- `/help`：在 TUI 内显示命令列表和控制键说明。
- `/config`：打开本地配置浏览器。
- `/pause`：暂停当前 quest（若未绑定 quest，会进入选择面板）。
- `/resume`：恢复已暂停/停止的 quest（若未绑定 quest，会进入选择面板）。
- `/stop`：停止当前 quest（若未绑定 quest，会进入选择面板）。
- `/stop <quest_id>`：停止指定 quest。
- 在输入框中输入 `/` 会显示实时命令列表；继续输入 `/re`、`/co` 等前缀时，会按前缀过滤命令行
- 在 home 模式下，`↑/↓` 和 `Tab` 只会切换“当前预览选中的 quest”，不会直接硬切换一个已经绑定中的 quest。
- 在 home 模式下，普通文本不会再隐式创建 quest，也不会隐式发消息；必须用 `/new <goal>` 创建，用 `/projects` 或 `/use <quest_id>` 绑定后再聊天。

如果你已经在某个 quest 中，`/pause`、`/resume`、`/stop` 默认作用于当前 quest。

页脚和欢迎区也会直接显示主要快捷提示：

- `Enter`：发送输入或确认选择
- `↑/↓`：浏览选择列表
- `Esc`：关闭当前弹层
- `Ctrl+O`：打开 Web 工作区
- `Ctrl+C`：退出 TUI

## 消息投递（Mailbox）模型

TUI、Web UI、以及外部 Connector 共用同一套“邮箱”语义：

1. 当 quest 空闲时，用户第一条普通消息会**直接触发一轮 turn**。
2. 这条启动消息会被本轮 run 认领，不会在后续“邮箱投递”中被重复投递。
3. 当 agent 正在运行时，后续用户消息会进入 `.ds/user_message_queue.json` 队列。
4. 这些排队消息只会在 agent 调用 `artifact.interact(...)` 时被投递给 agent。
5. 投递发生后，队列消息会从 `pending` 变成已完成的审计记录。
6. 如果没有新消息，运行时会明确告诉 agent“用户没有新消息”，便于继续推进而不是卡住等待。

相关持久化文件（均在 quest 内）：

- `.ds/runtime_state.json`
- `.ds/user_message_queue.json`
- `.ds/interaction_journal.jsonl`
- `.ds/events.jsonl`

## Pause / Stop / Resume

Quest 级控制：

- `/pause`：中断当前 runner，并将 quest 标记为 `paused`。
- `/resume`：把 `paused` 或 `stopped` 的 quest 重新置为 `active`。
- `/stop`：更强的中断；清理 `active_run_id`，把 quest 标记为 `stopped`。
- `/pause`、`/resume`、`/stop` 会写入一条可见的控制事件到 quest 历史，并按路由策略推送到绑定的 connectors。

`/stop` 比 `/pause` 更强：

- 未投递的邮箱消息会被取消（但会保留审计记录，如 `cancelled_by_stop`）
- 当前轮启动消息会记录为 `accepted_by_run`
- stop 后下一条新用户消息会启动新的一轮，不会静默重放旧队列
- stop 不会改写 Git：当前分支/工作树/已写文件都保留，便于继续接续

守护进程级 stop：

- `ds --stop`：停止守护进程
- 会尽量先优雅退出；必要时升级到 `SIGTERM`/`SIGKILL`
- 成功停止后会清理 daemon state，并打印 `DeepScientist daemon stopped.`

## Artifact 交互要求

agent 应当把 `artifact.interact(...)` 作为长对话的“脊柱”：

- `progress` / `milestone`：线程式进度更新（非阻塞）
- `decision_request`：阻塞式决策请求（需给出 1~3 个选项、利弊、证据）

## 排错

若你发送消息后 TUI 看起来“没反应”：

- 确认是否绑定了 quest
- 用 `/status` 查看 quest 状态
- 查看 `.ds/runtime_state.json`（`status`、`active_run_id`、`pending_user_message_count`）
- 查看 `.ds/events.jsonl` 是否有 `runner.turn_error`、`quest.control`、`artifact.recorded`

若“运行中”时发送的补充消息没有被 agent 看到：

- 看 quest 是否仍在运行
- 看 `.ds/user_message_queue.json`
- 确认 agent 过程中有调用 `artifact.interact(...)`
