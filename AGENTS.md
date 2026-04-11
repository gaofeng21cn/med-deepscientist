# Med Deepscientist Repository Agent Contract

This root `AGENTS.md` is the repository-native contract for direct sessions that enter from the project root, including Codex App and plain Codex sessions.

## Scope

Apply this file to the repository root and all descendants unless a deeper `AGENTS.md` overrides it for a narrower subtree.

## Project Truth

The authoritative project truth contract lives at `contracts/project-truth/AGENTS.md`.
Read that file first whenever repository-specific goals, architecture priorities, mutation rules, or domain constraints matter.

## OMX Historical Reference

OMX project-scope orchestration has been retired for this repository as of 2026-04-11.
Any OMX-specific artifacts should be treated as historical reference only, not as active workflow control.

Backup snapshot for the offboarding transition:
`/Users/gaofeng/workspace/_omx_offboarding_backup/2026-04-11-codex-reset/med-deepscientist`

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
