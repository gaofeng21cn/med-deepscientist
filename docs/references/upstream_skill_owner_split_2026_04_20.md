# 五个核心 Skill 的 owner split 参考

## 用途

这份清单用于区分三类内容：

- 哪些段落属于 `MedDeepScientist` 应继续承载的通用 research substrate
- 哪些规则应留在 `MedAutoScience` owner 层
- 哪些长段主要是 upstream 已成熟的方法论，后续若改成“引用 upstream protocol + 本地薄 overlay”时可以优先压薄

## 快照结论

- `baseline`、`analysis-campaign`、`decision`、`experiment` 当前在 `med-deepscientist/main` 与本地 `DeepScientist` 对应 skill 逐字一致。
- `write` 只有两处本地差异，而且这两处属于必要的 caption hygiene 修正：MDS 要求稿件表面保持 manuscript-native，不在 figure caption 里写 AutoFigure-Edit、服务推荐、URL 或生成来源。
- 医学稿件 owner 规则继续上移到 `MedAutoScience` overlay 和 publication gate，不回灌到 MDS base skill。

## Baseline

### MDS substrate

- 整份 [`src/skills/baseline/SKILL.md`](/Users/gaofeng/workspace/med-deepscientist/src/skills/baseline/SKILL.md) 归 MDS substrate。
- 关键承载面：
  - `## Required plan and checklist`
  - `## Required durable outputs`
  - `## File-by-file contract`
  - `## Durable path contract`
  - `## Workspace and branch rules`
  - `## Memory rules`
  - `## Artifact rules`

### MAS owner

- 医学 baseline 选择政策
- 医学 comparability 规则
- 医学证据接受门槛

### 可压薄参考

- `## Quick workflow`
- `## Fast-path first`
- `## Route order`
- `## Workflow`
- `## Feasibility and trust classes`
- `## Minimum baseline artifact content`
- `## Failure and blocked handling`
- `## Exit criteria`

## Analysis Campaign

### MDS substrate

- 整份 [`src/skills/analysis-campaign/SKILL.md`](/Users/gaofeng/workspace/med-deepscientist/src/skills/analysis-campaign/SKILL.md) 归 MDS substrate。
- 关键承载面：
  - `## Required plan and checklist`
  - `## Truth sources`
  - `## Required durable outputs`
  - `### 0. Launch the campaign durably`
  - `### 0.1 Bind the campaign to the selected outline when writing-facing`
  - `### 4. Record each analysis slice`
  - `## Memory rules`
  - `## Artifact rules`

### MAS owner

- 医学 follow-up analysis 类型
- 医学 slice 的 claim mapping
- 医学 manuscript placement 判断

### 可压薄参考

- `## Stage purpose`
- `## Quick workflow`
- `### 1. Define the campaign charter`
- `### 2. Split into isolated analysis runs`
- `### 3. Keep comparability`
- `### 5. Aggregate the campaign`
- `### 6. Route the next step`
- `## Analysis-quality rules`
- `## Failure and blocked handling`
- `## Exit criteria`

## Decision

### MDS substrate

- 整份 [`src/skills/decision/SKILL.md`](/Users/gaofeng/workspace/med-deepscientist/src/skills/decision/SKILL.md) 归 MDS substrate。
- 关键承载面：
  - `## Required decision record`
  - `## Allowed actions`
  - `## Truth sources`
  - `### 5. Request user input only when needed`
  - `### 6. Record the decision durably`
  - `## Memory rules`

### MAS owner

- 医学路线选择政策
- 医学 claim 的停止/降级标准
- guideline / journal / reviewer-facing 路由策略

### 可压薄参考

- `## Recommended verdicts`
- `### 1. State the question`
- `### 2. Collect the evidence`
- `### 3. Choose verdict and action`
- `### 3.1 Selection among candidate packages`
- `### 3.2 Research-route selection heuristic`
- `### 4. State the reason`
- `## Decision-quality rules`
- `## Exit criteria`

## Experiment

### MDS substrate

- 整份 [`src/skills/experiment/SKILL.md`](/Users/gaofeng/workspace/med-deepscientist/src/skills/experiment/SKILL.md) 归 MDS substrate。
- 关键承载面：
  - `## Required plan and checklist`
  - `## Working-boundary rules`
  - `## Resource and environment rules`
  - `## Truth sources`
  - `## Required durable outputs`
  - `### 3. Confirm the execution workspace`
  - `### 5. Execute the run`
  - `### 5.1 Long-running command protocol`
  - `### 5.2 Progress marker protocol`
  - `### 7. Record the run`
  - `## Acceptance gate`
  - `## Memory rules`
  - `## Artifact rules`

### MAS owner

- 医学实验设计的 domain constraints
- 医学运行资源策略
- 医学结果解释边界

### 可压薄参考

- `## Quick workflow`
- `## Experiment mental guardrails`
- `### 1. Define the run contract`
- `### 2. Run a preflight check`
- `### 2.1 Diagnostic mode trigger`
- `### 4. Implement the minimum required change`
- `### 6. Validate the outputs`
- `### 8. Decide the next move`
- `## Run-quality rules`
- `## Failure and blocked handling`
- `## Exit criteria`

## Write

### MDS substrate

- [`src/skills/write/SKILL.md`](/Users/gaofeng/workspace/med-deepscientist/src/skills/write/SKILL.md) 继续承载通用 writing runtime contract。
- 当前应保留的本地修正只有两处 caption hygiene：
  - `## Interaction discipline` 里要求 figure caption 保持 manuscript-native
  - `### Phase 6. Figures and tables` 里要求不追加 tool/vendor/service promotion、URL 或 provenance
- 关键承载面：
  - `## Preconditions and gate`
  - `## Truth sources`
  - `## Required durable outputs`
  - `## Required file expectations`
  - `## Memory rules`
  - `## Artifact rules`
  - `## Hard integrity rules`
  - `## Failure and blocked handling`
  - `## Exit criteria`

### MAS owner

- 医学 manuscript structure
- 医学 citation strategy
- 医学 claim-evidence map
- 医学 figures/tables 规范
- reviewer-first、readiness tiers、submission gate、medical closure owner boundary

这些内容当前应落在：

- [`src/med_autoscience/overlay/templates/medical-research-write.SKILL.md`](/Users/gaofeng/workspace/med-autoscience/src/med_autoscience/overlay/templates/medical-research-write.SKILL.md)
- [`src/med_autoscience/overlay/templates/medical-research-review.block.md`](/Users/gaofeng/workspace/med-autoscience/src/med_autoscience/overlay/templates/medical-research-review.block.md)
- [`src/med_autoscience/overlay/templates/medical-research-finalize.SKILL.md`](/Users/gaofeng/workspace/med-autoscience/src/med_autoscience/overlay/templates/medical-research-finalize.SKILL.md)

### 可压薄参考

- `## Writing mental guardrails`
- `## Paper experiment matrix contract`
- `## Venue template selection`
- `### Phase 0. Ordering discipline`
- `### Phase 1. Evidence assembly`
- `### Phase 2. Evidence-gap check`
- `### Phase 3. Storyline and outline`
- `### Phase 3.1 Outline selection rubric`
- `### Phase 4. Drafting`
- `### Phase 5. Citation integrity`
- `### Citation resources`
- `### Phase 6. Figures and tables`
- `### Phase 7. Claim-evidence map and self-review`
- `### Phase 7.5. Revision loop`
- `### Phase 8. Visual proofing`
- `### Phase 9. Submission gate`
- `## Extra references`

## 当前落点

- MDS 继续保留 runtime path、artifact API、memory discipline、branch/worktree、durable output schema。
- MAS 继续承接医学研究设计、医学证据规则、journal/reviewer policy、submission readiness。
- 这轮 skill 清理的原则是“保持 upstream 成熟内容原样吸收”，只保留必要且已经验证的本地分叉；当前这类必要分叉集中在 `write` 的 caption integrity 上。
