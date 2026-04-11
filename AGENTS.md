# Med Deepscientist Repository Contract

This root `AGENTS.md` is the default repository entry contract for direct sessions from the project root.

## Scope

Apply this file to the repository root and all descendants unless a deeper `AGENTS.md` overrides it for a narrower subtree.

## Project Role

- `med-deepscientist` is a controlled `DeepScientist`-derived runtime for `MedAutoScience`, not a large standalone platform.
- The authoritative runtime lives in Python under `src/deepscientist/`; `bin/ds.js` stays a thin npm launcher.
- Workflow control should stay prompt-led and skill-led. Avoid rebuilding a large central scheduler when prompts plus skills are sufficient.
- Each quest remains one Git repository with durable state inside the quest root.

## Priority Order

- First, improve `MedAutoScience -> MedDeepScientist` compatibility so this repo can serve as the default stable runtime surface.
- Second, reduce adapter debt, implicit layout assumptions, and duplicated runtime interpretation.
- Third, absorb upstream `DeepScientist` changes only when they have clear runtime value.

## Stable Runtime Guardrails

- The stable minimal adapter surface is defined in `docs/policies/runtime_protocol.md`. If behavior changes intentionally, update that document and the matching regression tests in the same change.
- Keep the public built-in MCP surface limited to `memory`, `artifact`, and `bash_exec`.
- Preserve the shared daemon contract for the web UI and TUI. If an API route changes, update the daemon, clients, and tests together.
- Do not move quest layout files casually. If `src/deepscientist/quest/layout.py` changes, update the affected services, consumers, and tests together.
- If code and docs diverge, prefer the current runtime behavior and tests, then bring the docs back into sync in the same change.

## Documentation And Reference Layers

- Public repository docs live under `docs/`; user-facing docs should stay under `docs/en/` and `docs/zh/`.
- Local planning material belongs under untracked `docs/superpowers/`, not tracked `docs/`.
- `contracts/project-truth/AGENTS.md` is the detailed appendix for subsystem-specific guardrails and long-range product truth when the root contract is not enough.
- OMX orchestration is retired in this repository. Historical OMX artifacts are reference-only.
- Backup snapshot for the offboarding transition: `/Users/gaofeng/workspace/_omx_offboarding_backup/2026-04-11-codex-reset/med-deepscientist`

## Working Agreements

- Keep diffs small, reviewable, and reversible.
- Prefer deletion over addition when simplification preserves behavior.
- Reuse existing patterns and utilities before introducing new abstractions.
- Do not add new dependencies without explicit justification.
- Run the relevant tests, type checks, and validation commands before claiming completion.
- Final reports should include what changed and any remaining risks or known gaps.

## Local State

- `.omx/` is retained only for local historical artifacts from the retired OMX workflow and must remain untracked.
- `.codex/` is local Codex tooling state and must remain untracked.
