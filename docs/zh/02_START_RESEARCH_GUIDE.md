# 02 Start Research 参考：如何填写科研启动合同

这份文档说明当前 `Start Research` 弹窗的真实结构，以及它到底会向后端提交什么。

实现来源：

- `src/ui/src/lib/startResearch.ts`
- `src/ui/src/components/projects/CreateProjectDialog.tsx`

## 这个弹窗实际做什么

`Start Research` 不只是“新建项目表单”，它同时完成四件事：

1. 收集结构化启动上下文
2. 把这些上下文编译成项目的第一条 kickoff prompt
3. 绑定一个可选的可复用 baseline
4. 持久化 `startup_contract`，供后续 prompt builder 持续读取

## 当前前端数据模型

### `StartResearchTemplate`

```ts
type StartResearchTemplate = {
  title: string
  quest_id: string
  goal: string
  baseline_id: string
  baseline_variant_id: string
  baseline_urls: string
  paper_urls: string
  runtime_constraints: string
  objectives: string
  need_research_paper: boolean
  research_intensity: 'light' | 'balanced' | 'sprint'
  decision_policy: 'autonomous' | 'user_gated'
  launch_mode: 'standard' | 'custom'
  custom_profile: 'continue_existing_state' | 'revision_rebuttal' | 'freeform'
  entry_state_summary: string
  review_summary: string
  custom_brief: string
  user_language: 'en' | 'zh'
}
```

关键变化：

- `scope`
- `baseline_mode`
- `resource_policy`
- `time_budget_hours`
- `git_strategy`

这几项已经不再由用户逐个填写，而是由 `research_intensity` 和是否选中 `baseline_id` 自动推导。

### 自动推导字段

```ts
type StartResearchContractFields = {
  scope: 'baseline_only' | 'baseline_plus_direction' | 'full_research'
  baseline_mode:
    | 'existing'
    | 'restore_from_url'
    | 'allow_degraded_minimal_reproduction'
    | 'stop_if_insufficient'
  resource_policy: 'conservative' | 'balanced' | 'aggressive'
  time_budget_hours: string
  git_strategy:
    | 'branch_per_analysis_then_paper'
    | 'semantic_head_plus_controlled_integration'
    | 'manual_integration_only'
}
```

推导逻辑在 `resolveStartResearchContractFields(...)`。

## 后端提交结构

前端最终会提交：

```ts
{
  title,
  goal: compiled_prompt,
  quest_id,
  requested_baseline_ref: {
    baseline_id,
    variant_id
  } | null,
  startup_contract: {
    schema_version: 3,
    user_language,
    need_research_paper,
    research_intensity,
    decision_policy,
    launch_mode,
    custom_profile,
    scope,
    baseline_mode,
    resource_policy,
    time_budget_hours,
    git_strategy,
    runtime_constraints,
    objectives: string[],
    baseline_urls: string[],
    paper_urls: string[],
    entry_state_summary,
    review_summary,
    custom_brief,
  }
}
```

## 字段说明

### 项目基本身份

**`title`**

- 项目的人类可读标题。
- 用于卡片和工作区标题。
- 不要求与 `quest_id` 一致。

**`quest_id`**

- 项目的稳定标识，保存在 `quest_id` 中，同时也是目录名。
- 默认由 runtime 提供下一个顺序编号。
- 允许用户手动覆盖。

**`goal`**

- 核心研究请求。
- 会成为 kickoff prompt 的主体。
- 好的写法：科学问题、目标、成功标准、研究边界。
- 不好的写法：直接写一堆过细的实现步骤。

**`user_language`**

- 声明后续 kickoff 和交流默认偏好的语言。

### Baseline 与参考资料

**`baseline_id`**

- 从 registry 中选择一个可复用 baseline。
- 一旦存在，推导出的 `baseline_mode` 会变成 `existing`。
- 运行时应优先 attach 并 verify 它，而不是从零开始。

**`baseline_variant_id`**

- baseline 条目中某个具体 variant 的选择器。

**`baseline_urls`**

- 当没有 registry baseline 时，作为恢复 baseline 的候选来源。
- 提交时转成 `string[]`。

**`paper_urls`**

- 论文、代码仓库、benchmark、leaderboard 等参考资料。
- 提交时转成 `string[]`。

### 约束与目标

**`runtime_constraints`**

- 硬约束，例如预算、硬件、隐私、存储、截止时间等。

**`objectives`**

- 每行一个目标。
- 提交时转成 `string[]`。
- 应该写“下一轮需要产出什么”，而不是写空泛口号。

**`need_research_paper`**

- `true`：默认继续推进到分析和写作准备
- `false`：默认追求最强且有依据的算法结果，不自动进入论文写作

### 高层控制项

**`research_intensity`**

- `light`
  - 推导结果：仅 baseline、保守、8 小时、手动集成
- `balanced`
  - 推导结果：baseline + 方向、平衡、24 小时、受控集成
- `sprint`
  - 推导结果：完整研究、激进、48 小时、analysis 分支优先

这是当前公开给用户的主要“轮次深度”控制杆。

**`decision_policy`**

- `autonomous`
  - 普通路线由 agent 自行决定
- `user_gated`
  - 只有真正依赖用户偏好时，才允许阻塞式决策请求

### 启动模式

**`launch_mode`**

- `standard`
  - 按默认科研主线启动
- `custom`
  - 不假设这是一个“从零开始”的普通科研任务

**`custom_profile`**

仅在 `launch_mode = custom` 时有效。

- `continue_existing_state`
  - 先审计已有 baseline、结果、草稿或混合资产
  - prompt builder 会显式引导 agent 优先打开 `intake-audit`
- `revision_rebuttal`
  - 这是一个审稿回复、revision、rebuttal 类型任务
  - prompt builder 会显式引导 agent 优先打开 `rebuttal`
- `freeform`
  - 以自定义 brief 为主，尽量少做额外假设

**`entry_state_summary`**

- 用自然语言概括当前已经存在什么。
- 典型内容：
  - 已有可信 baseline
  - 主实验已经跑完
  - 部分论文草稿已经存在
  - 部分补充图表已经存在

**`review_summary`**

- 主要用于 review / revision 场景。
- 用来概括 reviewer comments、修改要求、meta-review 约束。

**`custom_brief`**

- 一个额外的启动级说明。
- 用来覆盖或收窄默认的 blank-slate full-research 行为。

## 自动推导合同映射

当前 preset 映射如下：

| `research_intensity` | `scope` | `baseline_mode` | `resource_policy` | `time_budget_hours` | `git_strategy` |
|---|---|---|---|---:|---|
| `light` | `baseline_only` | `stop_if_insufficient` | `conservative` | `8` | `manual_integration_only` |
| `balanced` | `baseline_plus_direction` | `restore_from_url` | `balanced` | `24` | `semantic_head_plus_controlled_integration` |
| `sprint` | `full_research` | `allow_degraded_minimal_reproduction` | `aggressive` | `48` | `branch_per_analysis_then_paper` |

额外规则：

- 如果选中了 `baseline_id`，推导得到的 `baseline_mode` 会强制变成 `existing`

## Prompt 编译行为

`compileStartResearchPrompt(...)` 会生成一段可读 kickoff prompt，包含：

- 项目启动上下文
- 核心研究请求
- 研究目标
- baseline 上下文
- 参考论文 / 仓库
- 运行约束
- 研究交付模式
- 决策处理模式
- 启动模式
- 研究合同
- 必须遵守的工作规则

其中自定义启动会被明确写出来：

- `standard`
  - 告诉 agent 使用默认科研图谱
- `custom + continue_existing_state`
  - 告诉 agent 先整理和信任排序已有资产
  - 明确优先 `intake-audit`
- `custom + revision_rebuttal`
  - 告诉 agent 先理解 reviewer comments 和当前论文状态
  - 明确优先 `rebuttal`
- `custom + freeform`
  - 告诉 agent 以 custom brief 为主，只打开真正需要的 skills

## 示例 payload

### 标准启动

```json
{
  "title": "Sparse adapter robustness",
  "goal": "Investigate whether sparse routing improves robustness without hurting compute efficiency.",
  "quest_id": "012",
  "requested_baseline_ref": {
    "baseline_id": "adapter-baseline",
    "variant_id": "default"
  },
  "startup_contract": {
    "schema_version": 3,
    "user_language": "en",
    "need_research_paper": true,
    "research_intensity": "balanced",
    "decision_policy": "autonomous",
    "launch_mode": "standard",
    "custom_profile": "freeform",
    "scope": "baseline_plus_direction",
    "baseline_mode": "existing",
    "resource_policy": "balanced",
    "time_budget_hours": 24,
    "git_strategy": "semantic_head_plus_controlled_integration",
    "runtime_constraints": "One 24 GB GPU. Keep data local.",
    "objectives": [
      "verify the reusable baseline",
      "test one justified sparse-routing direction"
    ],
    "baseline_urls": [],
    "paper_urls": [
      "https://arxiv.org/abs/2401.00001"
    ],
    "entry_state_summary": "",
    "review_summary": "",
    "custom_brief": ""
  }
}
```

### 自定义启动：继续已有状态

```json
{
  "title": "Continue retrieval project",
  "goal": "Continue the existing retrieval project and decide whether a fresh main run is still needed.",
  "quest_id": "013",
  "requested_baseline_ref": null,
  "startup_contract": {
    "schema_version": 3,
    "user_language": "en",
    "need_research_paper": true,
    "research_intensity": "light",
    "decision_policy": "autonomous",
    "launch_mode": "custom",
    "custom_profile": "continue_existing_state",
    "scope": "baseline_only",
    "baseline_mode": "stop_if_insufficient",
    "resource_policy": "conservative",
    "time_budget_hours": 8,
    "git_strategy": "manual_integration_only",
    "runtime_constraints": "Do not rerun expensive full-corpus indexing unless evidence says the old run is unusable.",
    "objectives": [
      "normalize current evidence",
      "decide whether a new run is actually required"
    ],
    "baseline_urls": [],
    "paper_urls": [],
    "entry_state_summary": "Trusted baseline exists. One main run finished. Draft intro and method already exist.",
    "review_summary": "",
    "custom_brief": "Audit first. Only rerun if current metrics or artifacts are inconsistent."
  }
}
```

### 自定义启动：审稿 / rebuttal

```json
{
  "title": "Camera-ready revision",
  "goal": "Address reviewer requests, add only the missing evidence, and revise the manuscript cleanly.",
  "quest_id": "014",
  "requested_baseline_ref": null,
  "startup_contract": {
    "schema_version": 3,
    "user_language": "en",
    "need_research_paper": true,
    "research_intensity": "balanced",
    "decision_policy": "user_gated",
    "launch_mode": "custom",
    "custom_profile": "revision_rebuttal",
    "scope": "baseline_plus_direction",
    "baseline_mode": "restore_from_url",
    "resource_policy": "balanced",
    "time_budget_hours": 24,
    "git_strategy": "semantic_head_plus_controlled_integration",
    "runtime_constraints": "Only add experiments that directly answer reviewer concerns.",
    "objectives": [
      "map reviewer comments to concrete actions",
      "run only the necessary supplementary evidence",
      "update the draft and response letter"
    ],
    "baseline_urls": [],
    "paper_urls": [],
    "entry_state_summary": "A draft and previous experiment outputs already exist.",
    "review_summary": "Reviewers asked for one stronger ablation, one extra baseline, and a clearer limitation paragraph.",
    "custom_brief": "Treat the current manuscript and review packet as the active contract."
  }
}
```

## 运行时意义

- `startup_contract` 是项目的持久状态，不只是 UI 临时字段。
- 后续 prompt builder 还会继续读取 `launch_mode`、`custom_profile`、`entry_state_summary`、`review_summary`、`custom_brief`。
- 所以 `Start Research` 不只影响第一轮，还会影响后续路由判断。

## 修改检查清单

如果修改 `Start Research`，要同步检查：

- `src/ui/src/lib/startResearch.ts`
- `src/ui/src/components/projects/CreateProjectDialog.tsx`
- `src/prompts/system.md`（如果运行时解释变了）
- `src/deepscientist/prompts/builder.py`（如果 prompt 路由变了）
- 本文档
- `docs/en/02_START_RESEARCH_GUIDE.md`
- `tests/test_prompt_builder.py`
- `tests/test_stage_skills.py`
