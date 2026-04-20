# Upstream Intake Audit 2026-04-20

这份审计记录了 `MedDeepScientist` 在 2026-04-20 这轮对 `upstream/main` 的继续吸收、分支回收与主线收口结果。

## 快照

- audit_date: `2026-04-20`
- target_repo: `MedDeepScientist` (`med-deepscientist`)
- comparison_ref: `upstream/main`
- merge_base: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- comparison_window_before_round: `main@c2074db` vs `upstream/main@bfc8675`
- rev_list_before_round: `ahead=127, behind=132`
- execution_status: `absorbed_on_main_with_followup_round`
- main_head_after_round: `1a8139c`

## 证据

这轮 intake 基于以下 fresh checks 分类并执行：

```bash
git fetch upstream main --prune
git rev-list --left-right --count c2074db...bfc8675
git merge-base c2074db bfc8675
git show --no-patch --oneline bfc8675 411fd64 de258c9 7bed5c6 36b493a 39bd418 e1102a0 9222423 5ca5410
git branch -vv
git worktree list --porcelain
```

本轮还确认了一个重要验证约束：

- 默认 `Playwright` 基座 `http://0.0.0.0:20999` 可能指向仓库外部已经在运行的旧前端。
- `quest lazy-load` 这条 lane 的首次失败来自外部 `20999` 污染，真实 lane 验证需要改用当前 worktree / 当前 `main` 自己启动的 preview 端口。

## 吸收结果

### A. 先收口主线已有本地 closeout

1. 本地提交 `ebbd9da` `fix: sync paper metadata closeout mirrors`
   - decision: `absorb`
   - rationale:
     - 这是根仓已有未提交变更的直接收口，涉及 paper metadata closeout mirror 与对应测试。
     - 改动已经在 `main` 上 fresh 验证，属于当前 fork 自己的 runtime/closeout 可信度修复。

### B. 吸收 upstream UI build 环境对齐

1. upstream commit `bfc8675` `fix(ui-build): align browser env handling under vite`
   - decision: `absorb_adapted`
   - local commit: `20cb16a`
   - rationale:
     - 当前 fork 的 UI 运行在 Vite 下，浏览器侧 `process.env` 读取需要和 Vite env surface 对齐。
     - 这条改动边界清晰，只涉及 `src/ui/vite.config.ts` 与 API URL 读取逻辑，收益直接且验证成本低。

### C. 吸收 upstream quest detail lazy-load

1. upstream commit `411fd64` `perf(quest): lazy-load detail data and unblock quest routes`
   - decision: `absorb_adapted`
   - main commit: `05130c5`
   - rationale:
     - 价值点是 quest route 首屏只拉 canvas 所需数据，把 `workflow / memory / documents / branches` 推迟到 Details / Memory 视图。
     - 当前 fork 直接套这 5 个文件还不够，必须补齐 `src/ui/src/lib/acp.ts` 里的配套 hydration 顺序，特别是：
       - `historySeeded` 状态外露给 `QuestWorkspaceSurface`
       - bootstrap 顺序改成 `先 session / snapshot，再 seed 历史 feed`
       - event stream 延后到 `historySeeded` 之后启动
     - 这条 absorb 最终形成的本地结果是 upstream UI slice + fork 内必要 runtime 配套的组合。

### D. 顺手回收本地功能分支

1. local branch commit `43c157c` `fix: reconcile zero-activity zombie turns`
   - decision: `absorb`
   - main commit: `afb01eb`
   - rationale:
     - 用户要求“项目下很多分支，看看能不能都吸收回 main 并清理”，这条分支是 clean worktree 上的单提交有效修复。
     - 改动把 “turn 开始后一直零活动” 的 zombie run 也纳入 watchdog / daemon audit 回收逻辑，并补了精确测试。
     - 这条修复直接压实 runtime native truth 与 daemon reconciliation，符合当前 fork 的高价值边界。

## 明确延期

### A. start-research / deepxiv 相关修复

1. upstream commit `de258c9` `fix(start-research): unlock create once setup patch is ready`
2. upstream commit `7bed5c6` `fix(deepxiv): use live draft token and remove duplicate setup dialog`
   - decision: `defer_incompatible`
   - rationale:
     - 当前 fork 里只有 `src/ui/src/components/projects/CreateProjectDialog.tsx`。
     - upstream 对应修复依赖的 `DeepXivSetupDialog`、`benchAutoAssist*`、`setupQuestStillRunning` 状态链在当前 fork 并不存在。
     - 如果硬吸，会把产品面直接扩到当前 fork 没有维护的一整套 DeepXiv setup bridge。

### B. PR50 Claude / MiniMax 大包

1. upstream commit `36b493a` `Merge pull request #50 from droidlyx/feat_claude_minimax_support`
2. upstream commit `39bd418` `rebase PR50 changes cleanly onto origin/main`
   - decision: `defer_split_needed`
   - rationale:
     - 这是一整包 provider / product / prompt / runtime surface 扩面。
     - 当前轮只保留“未来拆小 slice 再吸”的结论，不做整包 intake。

### C. Windows WSL skill / docs 线

1. upstream commit `e1102a0` `feat: add Windows WSL2 setup skill for AI coding agents`
2. upstream commit `9222423` `Merge pull request #53 from giao-123-sun/feat/windows-wsl-setup-skill`
3. upstream commit `5ca5410` `Merge branch 'main' into feat/windows-wsl-setup-skill`
   - decision: `defer`
   - rationale:
     - 这组改动主要是技能与文档扩面，不属于当前 `MAS -> MedDeepScientist` runtime seam 的第一优先级。
     - 当前轮优先把 runtime、UI lazy-load 与已存在本地分支收口。

## 执行路径

本轮采用了多 worktree 并行、完成后立刻吸回 `main` 的收口方式：

1. `codex/ui-build-env-alignment`
   - 完成 `20cb16a`
   - `git merge --ff-only` 吸回 `main`

2. `codex/quest-details-lazy-load`
   - 完成 `ad28592`
   - 因 `main` 已前进到 `20cb16a`，无法再 `ff-only`
   - 改为把单提交 `ad28592` cherry-pick 到 `main`
   - 形成主线提交 `05130c5`

3. `fix/zombie-run-stale-guard`
   - clean worktree，单提交 `43c157c`
   - 直接 cherry-pick 到 `main`
   - 形成主线提交 `afb01eb`

4. `codex/start-research-dialog-fixes`
   - 本轮只做结构兼容性审计
   - 结论是 `defer_incompatible`
   - 不吸收代码，只保留审计结论并进入 cleanup

## 验证

### 本地 closeout mirror 收口

```bash
uv run pytest -q tests/test_memory_and_artifact.py -k 'nonblocking_metadata_closeout or mirror_resync or metadata_closeout_from_submission_minimal_manifest or resynchronizes_stale_paper_line_mirrors'
uv run pytest -q tests/test_memory_and_artifact.py -k 'paper_contract_health or paper_line_state_sync or metadata_closeout'
scripts/verify.sh smoke
```

关键结果：

- `2 passed`
- `17 passed, 114 deselected`
- `55 passed`

### quest lazy-load lane worktree 验证

```bash
cd src/ui
npm run build
E2E_BASE_URL=http://0.0.0.0:21999/ui ./node_modules/.bin/playwright test e2e/quest-workspace-lazy-load.spec.ts
```

关键结果：

- `npm run build`: success
- `quest-workspace-lazy-load.spec.ts`: `1 passed`

### main 吸收后 fresh 验证

```bash
scripts/verify.sh smoke
cd src/ui
npm run build
E2E_BASE_URL=http://0.0.0.0:22001/ui ./node_modules/.bin/playwright test e2e/quest-workspace-lazy-load.spec.ts
uv run pytest -q tests/test_daemon_api.py -k 'test_quest_runtime_audit_reconciles_zero_activity_zombie_live_turn'
uv run pytest -q tests/test_runtime_native_truth.py -k 'test_watchdog_uses_turn_start_age_when_first_activity_never_arrives'
```

关键结果：

- `scripts/verify.sh smoke`: `55 passed`
- `src/ui npm run build`: success
- `quest-workspace-lazy-load.spec.ts`: `1 passed`
- `tests/test_daemon_api.py -k test_quest_runtime_audit_reconciles_zero_activity_zombie_live_turn`: `1 passed`
- `tests/test_runtime_native_truth.py -k test_watchdog_uses_turn_start_age_when_first_activity_never_arrives`: `1 passed`

## 下一步

- 这轮已经把当前确认有价值的 UI build、quest lazy-load、zero-activity zombie-turn 修复都落到 `main`。
- 后续继续扫 upstream 时，优先从 `PR50` 大包里拆独立 runtime slice，再重新评估。
- `start-research / deepxiv` 相关修复要等当前 fork 先明确是否真的引入那套产品结构，再决定是否继续 intake。
