# 02 Start Research Guide: Fill the Start Research Contract

This page documents the current `Start Research` dialog and the exact startup contract it submits.

Implementation sources:

- `src/ui/src/lib/startResearch.ts`
- `src/ui/src/components/projects/CreateProjectDialog.tsx`

## What the dialog does

`Start Research` is not only a “new project” form. It does four things together:

1. collects structured kickoff context
2. compiles that context into the first project prompt
3. binds an optional reusable baseline
4. persists a structured `startup_contract` for later prompt building

## Current frontend model

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

Important point: `scope`, `baseline_mode`, `resource_policy`, `time_budget_hours`, and `git_strategy` are no longer edited directly in the form. They are derived from `research_intensity` plus whether a reusable baseline is selected.

### Derived contract fields

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

Resolution logic lives in `resolveStartResearchContractFields(...)`.

## Backend payload

The dialog submits:

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

## Field reference

### Core project identity

**`title`**

- Human-readable project title.
- Used in cards and workspace headers.
- Does not need to equal `quest_id`.

**`quest_id`**

- Stable project identifier stored in `quest_id` and used as the directory name.
- By default the runtime suggests the next sequential id.
- Manual override is allowed.

**`goal`**

- Main scientific request.
- This becomes the central body of the compiled kickoff prompt.
- Good input: scientific question, target, success condition, boundary.
- Bad input: low-level implementation instructions with no research framing.

**`user_language`**

- Declares the preferred user-facing language for kickoff and later interaction.

### Baseline and references

**`baseline_id`**

- Selects a reusable baseline from the registry.
- When present, derived `baseline_mode` becomes `existing`.
- Runtime should attach and verify this baseline before ordinary downstream work.

**`baseline_variant_id`**

- Optional variant selector inside a baseline entry.

**`baseline_urls`**

- Fallback source links when there is no registered reusable baseline.
- Submitted as `string[]`.

**`paper_urls`**

- Papers, repos, benchmarks, or leaderboards that shape early scouting.
- Submitted as `string[]`.

### Constraints and objectives

**`runtime_constraints`**

- Hard constraints such as budget, hardware, privacy, storage, or deadlines.

**`objectives`**

- One goal per line.
- Submitted as `string[]`.
- This should state the next meaningful outcomes, not generic aspirations.

**`need_research_paper`**

- `true`: the project should keep going through analysis and writing readiness.
- `false`: optimize for the strongest justified algorithmic result and avoid default paper routing.

### High-level control knobs

**`research_intensity`**

- `light`
  - derived contract: baseline-only, conservative, 8h, manual integration
- `balanced`
  - derived contract: baseline-plus-direction, balanced, 24h, controlled integration
- `sprint`
  - derived contract: full research, aggressive, 48h, branch-per-analysis

This is the main public knob for round depth.

**`decision_policy`**

- `autonomous`
  - the agent should keep choosing ordinary routes on its own
- `user_gated`
  - the agent may raise a blocking decision only when continuation truly depends on the user

### Launch mode

**`launch_mode`**

- `standard`
  - start from the ordinary canonical research loop
- `custom`
  - do not assume a blank-slate launch; use the extra custom-entry fields

**`custom_profile`**

Only meaningful when `launch_mode = custom`.

- `continue_existing_state`
  - start by auditing existing baselines, results, drafts, or mixed project assets
  - prompt builder should steer the agent toward `intake-audit`
- `revision_rebuttal`
  - start from reviewer comments, revision packets, or a rebuttal task
  - prompt builder should steer the agent toward `rebuttal`
- `freeform`
  - follow a custom brief with minimal forced workflow assumptions

**`entry_state_summary`**

- Plain-language summary of what already exists.
- Typical content:
  - trusted baseline exists
  - main run already finished
  - partial draft already exists
  - supplementary figures already exist

**`review_summary`**

- Only meaningful for review-driven work.
- Summarizes reviewer requests, revision demands, or meta-review constraints.

**`custom_brief`**

- Extra launch-time instruction that can narrow or override the default blank-slate full-research path.

## Derived contract mapping

Current preset mapping:

| `research_intensity` | `scope` | `baseline_mode` | `resource_policy` | `time_budget_hours` | `git_strategy` |
|---|---|---|---|---:|---|
| `light` | `baseline_only` | `stop_if_insufficient` | `conservative` | `8` | `manual_integration_only` |
| `balanced` | `baseline_plus_direction` | `restore_from_url` | `balanced` | `24` | `semantic_head_plus_controlled_integration` |
| `sprint` | `full_research` | `allow_degraded_minimal_reproduction` | `aggressive` | `48` | `branch_per_analysis_then_paper` |

Override rule:

- if `baseline_id` is selected, derived `baseline_mode` becomes `existing`

## Prompt compilation behavior

`compileStartResearchPrompt(...)` writes a human-readable kickoff prompt containing:

- project bootstrap
- primary research request
- research goals
- baseline context
- reference papers / repositories
- operational constraints
- research delivery mode
- decision handling mode
- launch mode
- research contract
- mandatory working rules

Custom launch behavior is explicit:

- `standard`
  - tells the agent to use the ordinary research graph
- `custom + continue_existing_state`
  - tells the agent to audit and normalize existing assets first
  - explicitly prefers `intake-audit`
- `custom + revision_rebuttal`
  - tells the agent to interpret reviewer comments and current paper state first
  - explicitly prefers `rebuttal`
- `custom + freeform`
  - tells the agent to follow the custom brief and open only the necessary skills

## Example payloads

### Standard launch

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

### Custom launch: continue existing state

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

### Custom launch: revision / rebuttal

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

## Operational implications

- The startup contract is durable project state, not only UI state.
- Prompt building later reads `launch_mode`, `custom_profile`, and related summaries again.
- This means `Start Research` shapes not just the first turn, but later routing decisions too.

## Validation checklist

When changing `Start Research`, update together:

- `src/ui/src/lib/startResearch.ts`
- `src/ui/src/components/projects/CreateProjectDialog.tsx`
- `src/prompts/system.md` if runtime interpretation changes
- `src/deepscientist/prompts/builder.py` if prompt routing changes
- this document
- `docs/zh/02_START_RESEARCH_GUIDE.md`
- related tests in `tests/test_prompt_builder.py` and `tests/test_stage_skills.py`
