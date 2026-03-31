# med-deepscientist Repository Guide

This `AGENTS.md` applies to the entire repository.

## Mission

Build `med-deepscientist` as a controlled DeepScientist-derived runtime that:

- runs on the user's machine by default
- installs cleanly through npm
- keeps the authoritative runtime in Python
- uses prompt- and skill-led workflow control
- stores durable state in files plus Git
- supports a full research loop inside one quest workspace

The target is a focused runtime layer for `MedAutoScience`, not a large independent platform.

## Public Repository Rules

- Do not commit local workstation-specific absolute paths.
- Do not commit generated artifacts such as `node_modules/`, `dist/`, `.turbo/`, `__pycache__/`, or `.pytest_cache/`.
- User-facing docs belong in `docs/en/` and `docs/zh/`.
- Internal planning notes, temporary specs, and one-off implementation checklists should not live under `docs/`.
- When code and docs diverge, prefer the current runtime behavior and tests, then update the docs in the same change.

## Source Of Truth

Start with the files that actually exist in this checkout:

- `README.md`
- `docs/en/ARCHITECTURE.md`
- `docs/en/DEVELOPMENT.md`
- `docs/en/TUI_USAGE.md`
- `docs/en/SETTINGS_REFERENCE.md`
- `src/deepscientist/`
- `src/deepscientist/runtime_tools/`
- `src/prompts/`
- `src/skills/`
- `src/ui/src/`
- `src/tui/`
- `tests/`

Do not add references to deleted or private local files.

## Core Contracts

### 1. One quest = one Git repository

- Every quest has one absolute `quest_root`.
- All durable quest content stays inside that quest root.
- Branches and worktrees express divergence inside that quest repository.

### 2. Python runtime, npm launcher

- The authoritative runtime lives under `src/deepscientist/`.
- `bin/ds.js` remains a thin launcher over the Python daemon and built UI bundles.
- Compatibility package names such as `@researai/deepscientist` and the `ds` CLI may remain until downstream cutover is complete.
- Public npm installs must ship prebuilt `src/ui/dist/` and `src/tui/dist/` bundles.
- Do not rely on end-user `postinstall` builds for the public npm path.

### 3. Only three public built-in MCP namespaces

Keep the public built-in MCP surface limited to:

- `memory`
- `artifact`
- `bash_exec`

Git behavior belongs inside `artifact`.
Durable shell execution belongs inside `bash_exec`.

### 4. Prompt-led, skill-led workflow

- The prompt defines workflow expectations and filesystem contract.
- Skills provide specialized execution behavior.
- The daemon persists, restores, and routes state, but should stay thin.
- Avoid hard-coding a large central stage scheduler when prompt plus skills are enough.

### 5. Registry-first extension points

Prefer small registries for:

- runners
- channels
- connector bridges
- skill discovery
- managed local runtime tools
- optional plugin adapters

Prefer `register_*()`, `get_*()`, and `list_*()` APIs over large dispatch branches.

### 6. Shared web and TUI contract

- The web UI and TUI must consume the same daemon API and event model.
- If an API route changes, update the daemon, web client, TUI client, and tests together.
- Preserve `/projects` and `/projects/:projectId` style routing in the web workspace.

### 7. QQ is first-class, but still generic

- QQ support is part of the core product shape.
- It should still fit the generic channel and bridge model instead of becoming a separate one-off runtime.

## Repository Layout

Important directories:

- `assets/`
- `bin/`
- `docs/`
- `src/deepscientist/`
- `src/prompts/`
- `src/skills/`
- `src/ui/`
- `src/tui/`
- `tests/`

Important runtime entry points:

- launcher: `bin/ds.js`
- CLI: `src/deepscientist/cli.py`
- daemon: `src/deepscientist/daemon/app.py`
- API router: `src/deepscientist/daemon/api/router.py`
- API handlers: `src/deepscientist/daemon/api/handlers.py`
- prompt builder: `src/deepscientist/prompts/builder.py`
- system prompt: `src/prompts/system.md`
- managed local tools: `src/deepscientist/runtime_tools/`

## Runtime Layout

Default runtime data lives under:

- `~/DeepScientist/runtime/`
- `~/DeepScientist/config/`
- `~/DeepScientist/memory/`
- `~/DeepScientist/quests/`
- `~/DeepScientist/plugins/`
- `~/DeepScientist/logs/`
- `~/DeepScientist/cache/`

Each `~/DeepScientist/quests/<quest_id>/` directory is its own Git repository.

## Quest Layout Contract

The quest scaffold in `src/deepscientist/quest/layout.py` defines the durable layout.

Important files:

- `quest.yaml`
- `brief.md`
- `plan.md`
- `status.md`
- `SUMMARY.md`

Important quest runtime directories:

- `artifacts/`
- `baselines/`
- `experiments/`
- `literature/`
- `handoffs/`
- `paper/`
- `memory/`
- `.ds/`

Do not move runtime files casually. If layout changes, update the services, API consumers, UI, TUI, and tests together.

## Skills

First-party stage skills live under `src/skills/`.

The standard research skills are:

- `scout`
- `baseline`
- `idea`
- `experiment`
- `analysis-campaign`
- `write`
- `finalize`
- `decision`

If you add or rename a stage skill:

- update the standard skill list
- update installer behavior
- update prompt builder output
- update tests

## Documentation Rules

- Keep public docs clear and task-oriented.
- Prefer English and Chinese user docs under `docs/en/` and `docs/zh/`.
- Maintainer-facing source-of-truth docs live in:
  - `docs/en/ARCHITECTURE.md`
  - `docs/en/DEVELOPMENT.md`
- Keep docs names stable when they are linked from the UI.
- If a document is implementation planning rather than user guidance, keep it out of `docs/`.

## Working Rules By Subsystem

### Quests, state, and Git

- Preserve the quest-per-repository model everywhere.
- Route Git-backed durable state through `artifact` and `gitops`.
- If quest layout changes, update snapshot generation and route consumers.

### MCP

- Keep public built-in MCP limited to `memory`, `artifact`, and `bash_exec`.
- Keep quest-aware context explicit through `McpContext`.

### Prompts and skills

- Keep workflow logic primarily in prompts and skills.
- When prompt behavior changes, update the relevant skill docs and tests.

### Runners

- Use the runner registry for new backends.
- Do not describe a runner as implemented until wiring and tests exist.

### Connectors and bridges

- Connector defaults belong in `src/deepscientist/config/models.py`.
- Validation belongs in `src/deepscientist/config/service.py`.
- User-facing delivery belongs in channels.
- Provider adaptation belongs in bridges.

### Managed local runtime tools

- Keep optional local tool installs behind `src/deepscientist/runtime_tools/`.
- Register new tools through the runtime tool registry instead of scattering ad hoc install logic.
- Reuse `RuntimeToolService` for status, install, and binary resolution.
- Document user-visible install or troubleshooting changes in docs.

### UI and TUI

- Preserve the shared contract between the two clients.
- If an API route changes, update the route, clients, and tests together.

## Change Checklists

When changing quest layout or durable state:

- update `src/deepscientist/quest/layout.py`
- update `src/deepscientist/quest/service.py`
- update snapshot consumers if fields changed
- update `tests/test_init_and_quest.py`
- update `tests/test_daemon_api.py`

When changing artifact or interaction behavior:

- update `src/deepscientist/artifact/schemas.py`
- update `src/deepscientist/artifact/service.py`
- update `src/deepscientist/mcp/server.py` if the tool contract changes
- update UI and TUI event rendering if payloads change
- update `tests/test_memory_and_artifact.py`
- update `tests/test_mcp_servers.py`
- update `tests/test_daemon_api.py`

When changing prompts or stage skills:

- update `src/prompts/system.md` or `src/deepscientist/prompts/builder.py`
- update `src/skills/<skill_id>/SKILL.md`
- keep installer and mirrored skill behavior in sync
- update `tests/test_stage_skills.py`
- update `tests/test_prompt_builder.py`

When changing connectors:

- update defaults in `src/deepscientist/config/models.py`
- update validation/help text in `src/deepscientist/config/service.py`
- update `src/deepscientist/channels/`
- update `src/deepscientist/bridges/`
- update connector tests

When changing managed local tools:

- update `src/deepscientist/runtime_tools/`
- update the concrete tool adapter such as `src/deepscientist/tinytex.py` if needed
- update any callers in CLI, doctor, or runtime services
- update maintainer docs:
  - `docs/en/ARCHITECTURE.md`
  - `docs/en/DEVELOPMENT.md`
- update user docs if install or troubleshooting changes are user-visible
- update or add tests for registration, status, install, and binary resolution

When changing API surface used by web and TUI:

- update `src/deepscientist/daemon/api/router.py`
- update `src/ui/src/lib/api.ts`
- update the TUI client code
- update contract tests such as `tests/test_api_contract_surface.py`

## Packaging And Release

- Keep the npm package release-oriented.
- Run `npm pack --dry-run` before treating packaging work as done.
- Keep README install instructions aligned with `package.json`.
- Keep `LICENSE` and package metadata aligned with the actual open-source license.

## Contribution Guideline Reference

For contributor workflow and pull request expectations, see `CONTRIBUTING.md`.
