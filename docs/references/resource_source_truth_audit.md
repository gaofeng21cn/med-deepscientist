# Resource And Source-Truth Audit Board

owner: MedDeepScientist maintainers
purpose: Track repo-tracked resource ownership, release artifact exceptions, and duplicate UI/branding/hero asset follow-up without moving assets during runtime hygiene work.
state: active audit board
machine boundary: human_doc:resource_source_truth_audit; machine enforcement lives in `scripts/repo_hygiene_policy.json` and `scripts/audit_repo_hygiene.py`.

## Current Enforced Hygiene

- Root `.agent-contract-baseline.json` is retired and must stay untracked.
- Tracked local/runtime state is forbidden for `.codex/`, `.omx/`, `.runtime-program/`, `runtime-state/`, `__pycache__/`, `*.egg-info`, `.DS_Store`, `build/`, and `out/`.
- Tracked `dist/` is only allowed under:
  - `src/ui/dist/`: npm release package source, required by `package.json` and `scripts/build-release.mjs`.
  - `src/tui/dist/`: npm release package source, required by `package.json` and `scripts/build-release.mjs`.
  - `src/ui/vendor/novel-headless/dist/`: vendored UI dependency artifact owned by the UI vendor subtree.

## Duplicate Resource Follow-Up Board

No resources are moved in this lane. The current follow-up candidates are:

| Area | Current Duplicate / Parallel Sources | Owner Signal | Follow-Up |
| --- | --- | --- | --- |
| Branding logo set | `assets/branding/logo.svg`, `assets/branding/logo-inverted.svg`, `assets/branding/logo-raster.png`, mirrored under `src/ui/public/assets/branding/` | UI/release packaging plus root assets | Decide whether root branding or UI public branding is the canonical source, then add a manifest-backed copy/build rule before deleting mirrors. |
| Deepscientist mark | `assets/branding/deepscientist-mark.png`, `src/ui/public/assets/branding/deepscientist-mark.png`, `assets/DeepScientist.png` | Product branding | Identify the canonical product mark and mark legacy variants before any UI import rewrite. |
| Projects image | `assets/branding/projects.png`, `docs/assets/branding/projects.png` | Public docs plus branding assets | Keep docs copy stable until docs image references are audited; then convert to one canonical docs source or generated copy. |
| Hero bitmaps | `assets/hero/*.png`, `src/ui/public/hero/*.png` | UI landing bundle plus root asset archive | Preserve UI build now; later choose whether root hero assets are source originals or redundant package mirrors. |
| Agent logos | `src/ui/public/agent-logos/*.png`, `src/ui/public/agent-logos/*.svg`, `src/ui/public/agent-logos/困/*.png` | UI public assets | Audit active imports and locale/legacy intent before pruning alternate raster/SVG/name variants. |
| Connector screenshots and diagrams | `docs/images/connectors/`, `docs/images/weixin/`, `docs/images/qq/`, `assets/branding/connector-*.png` | Docs/user guide assets | Keep docs-owned screenshots separate from UI branding until a manifest records purpose and freshness. |

## Next Gate

Before any resource movement, add a machine-readable asset manifest that records canonical owner, package inclusion, active imports, and docs references. Resource dedupe should then be validated with UI/TUI release build checks rather than prose-only review.
