# Upstream Intake Audit 2026-04-20 Follow-up

这份 follow-up 记录了 2026-04-20 主轮 intake 落到 `main` 之后，对剩余 upstream 候选和远端分支做的继续筛查、以及最终继续吸收的两个小 slice。

## 快照

- audit_date: `2026-04-20`
- target_repo: `MedDeepScientist` (`med-deepscientist`)
- comparison_ref: `upstream/main`
- fork_head_before_followup: `19bea39`
- comparison_head: `bfc8675`
- rev_list_main_vs_upstream_after_followup: `ahead=136, behind=132`
- execution_status: `focused_ui_tui_followup_absorbed_on_main`
- main_head_after_followup: `1a8139c`

## 证据

这轮 follow-up 基于以下 fresh checks 分类并执行：

```bash
git fetch --all --prune --tags
git rev-list --left-right --count main...upstream/main
git log --oneline main..upstream/main
git show --no-patch --oneline 3037b53 5247232 a973682 13fa853 d3b06e2 77e97d9 d58a655 d9d4bd6
git branch -vv
git worktree list --porcelain
```

继续审计时还核对了当前 fork 的真实文件面：

- `src/ui/src/lib/safe-json.ts` 在 follow-up 前并不存在，`QuestStageSurface`、`lab.ts`、`tabs.ts` 仍保留直接 `JSON.stringify(...)` 的脆点。
- `src/tui/src/app/AppContainer.tsx` 在 follow-up 前仍保留 `configMode === 'browse' || canBrowseHomeQuests` 这一组全局箭头条件，会和 `QuestScreen` 自己的箭头处理重叠。
- `CreateProjectDialog`、`DeepXivSetupDialog`、`BenchStoreDialog`、`setupQuestStillRunning` 这条产品链在当前 fork 里依旧不成体系，所以相关 upstream UI 修复继续延期。

## 候选决策

### Candidate A: frontend circular-safe serialization

- source commit: `3037b537c5ff7ebff10fc89d315aa95614513798`
- title: `fix: harden frontend circular-safe serialization`
- decision: `absorb_adapted`
- local commit: `945206f`
- rationale:
  - 当前 fork 的 `QuestStageSurface`、`lab.ts` 与 tabs 持久化仍直接依赖 `JSON.stringify(...)`，循环对象会把 workspace details、lab 摘要和 custom tabs 判等打崩。
  - 这条改动的价值集中在前端 helper 和少量调用点替换，不依赖 `DeepXiv`、`BenchStore` 或 runtime contract 改动。
  - 当前 fork 的 `toast.tsx` 已经绕开对象 stringify，所以 follow-up 只吸收仍然真实缺口的部分。

### Candidate B: TUI quest-browser arrow handling

- source commit: `52472325aeeda8e17ff23b7155073aa9724ba246`
- title: `fix: Prevent double arrow key events in quest browser panel`
- decision: `absorb`
- local commit: `1a8139c`
- rationale:
  - 当前 fork 的 `QuestScreen` 自己已经处理上下箭头，但 `AppContainer` 还会在 `questPanelMode` 打开时继续吃同一组全局箭头事件。
  - follow-up 把全局条件收紧到 `configMode === 'browse' && !questPanelMode`，一键只移动一项，边界清晰，风险极低。

## 明确延期

### Candidate C: BenchStore / start-research setup chain

- source commits:
  - `d3b06e259128bcde38b6ad986a062573fe5d85be`
  - `a973682ec631f120e5ac25155152765ae2daed58`
  - `13fa853f22dbfd71d73c284c0cdaf78d6ec22096`
- decision: `defer_incompatible`
- rationale:
  - 这组提交依赖 `BenchStoreDialog`、`setupQuestId`、`start_setup_patch`、`setupQuestStillRunning` 等产品状态链。
  - 当前 fork 没有维护那条完整产品面，直接 intake 会把受控 runtime fork 推向一条新的 setup/product ownership 线。

### Candidate D: workspace-mode / continuation-policy bundle

- source commits:
  - `d58a65584fc7e958f2363e9110c726823b64a4e2`
  - `d9d4bd6b8b9654f4409eb7ff673c9ecadc301cbf`
- decision: `defer_incompatible`
- rationale:
  - 当前 fork 继续把 `workspace_mode` 用在 research/worktree 状态命名空间。
  - upstream 这组提交把它当成 runtime control surface，语义依旧分叉，继续直接吸收会混淆持久化字段权责。

### Candidate E: DeepXiv settings and setup flow

- source commit: `77e97d995d57886aad5b49d46b620e43d38b011e`
- decision: `defer`
- rationale:
  - 这条提交会同时扩 config、settings UI、setup flow 与静态资源。
  - 当前 fork 的第一优先级仍是 `MAS -> MedDeepScientist` runtime seam，继续推产品扩面收益不成比例。

## 执行结果

这轮 follow-up 采用两个独立 worktree 并行落地、随后立即吸回 `main` 的方式：

1. `codex/ui-safe-json`
   - 完成 `6d954e9` `fix(ui): harden circular-safe serialization`
   - cherry-pick 到 `main`
   - 形成主线提交 `945206f`

2. `codex/tui-quest-browse-keys`
   - 完成 `ee615ea` `fix(tui): avoid double quest browser arrow handling`
   - cherry-pick 到 `main`
   - 形成主线提交 `1a8139c`

## 验证

### UI circular-safe serialization lane

```bash
cd src/ui
npm run build
uv run pytest -q tests/test_ui_source_contracts.py
git diff --check
```

关键结果：

- `src/ui npm run build`: success
- `tests/test_ui_source_contracts.py`: `1 passed`
- `git diff --check`: clean

### TUI quest-browser arrow lane

```bash
npm --prefix src/tui run build
uv run pytest -q tests/test_api_contract_surface.py -k tui_client_and_git_canvas_follow_same_protocol_contract
git diff --check
```

关键结果：

- `npm --prefix src/tui run build`: success
- `tests/test_api_contract_surface.py -k tui_client_and_git_canvas_follow_same_protocol_contract`: `1 passed, 14 deselected`
- `git diff --check`: clean

## 结论

- 经过这轮 follow-up，当前窗口里继续值得吸收的 upstream 小 slice 已经落到 `main`。
- 剩余未吸收候选继续集中在 `BenchStore / DeepXiv / workspace_mode` 这三组产品或 contract 扩面，后续应保持按需拆分、按兼容性门槛再审。
