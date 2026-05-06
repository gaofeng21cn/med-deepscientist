# Upstream Intake Audit 2026-04-30

这份审计记录了 `MedDeepScientist` 在 2026-04-30 对 `upstream/main` 的 latest-update learning round。

## 快照

- audit_date: `2026-04-30`
- target_repo: `MedDeepScientist` (`med-deepscientist`)
- comparison_ref: `upstream/main`
- comparison_head: `1f042ef` `docs: expand provider setup guidance`
- previous_intake_head: `d22165e` `docs: explain workspace explorer file visibility`
- local_main_at_audit: `0ed3be9` `Add Codex progress markers to telemetry`
- origin_main_at_audit: `bc117ed` `Speed up daemon resume control path`
- merge_base: `a7853fda3432d37f6dee91fa6e66330f564bd8be`
- rev_list_before_round: `ahead=229, behind=197`
- execution_status: `mas_contract_template_recorded_no_mds_code_slice`
- mds_code_landing: `none`

## Fresh Audit Commands

```bash
git fetch upstream --prune
git rev-list --left-right --count main...upstream/main
git log --reverse --oneline d22165e..upstream/main
git show --stat --oneline d22165e..upstream/main
uv run python -m med_autoscience.cli backend-upgrade-check --profile /Users/gaofeng/workspace/Yang/NF-PitNET/ops/medautoscience/profiles/nfpitnet.workspace.toml --refresh
```

Observed gate state:

- `git fetch upstream --prune` updated `upstream/main` to `1f042ef` at `2026-04-30 21:01:46 +0800`.
- Later GitHub SSH/HTTPS refresh attempts failed with connection-closed / SSL errors, so the MAS `--refresh` gate returned `blocked_refresh_failed`.
- The non-refresh MAS gate on the fetched local refs returned `upgrade_available` with `run_controlled_fork_intake_workflow`.

The code decision below therefore uses the already fetched `upstream/main@1f042ef` ref, and does not claim a fully refreshed remote gate after the network failure.

## Decision Matrix

### A. Adopted By MAS Contract / Template Record

1. upstream `64e7643` `feat(paper): add academic outline artifact gates`
2. upstream `77cbb00` `skills: add academic paper outline workflow`
3. upstream `bf7f408` `Improve paper quality review prompts`

- decision: `adopt_contract_template`
- owner_surface: `MAS eval_hygiene / controller_charter / workspace_projection`
- learned_capability: paper planning should separate `paper_view` from `evidence_view`; a mature paper outline should carry a one-sentence paper idea, scoped claims, method abstraction, evaluation plan, reviewer-facing analysis plan, evidence grounding, novelty boundary, reviewer objections, and manuscript language firewall.
- local landing: no MDS runtime code was absorbed in this round. The lesson is recorded in `med-autoscience/docs/program/deepscientist_learning_intake_2026_04_30.md` and guarded by MAS meta test coverage.
- rationale: the upstream implementation touches a large, divergent `artifact.service` surface. The safe intake path is to keep the lesson at MAS owner truth first, then consider a future narrow MDS runtime slice only if MAS needs a callable `validate_academic_outline` / `validate_manuscript_language` surface.

### B. Already Covered Or Stronger Locally

1. upstream `8451c14` / `a29f8a3` / merge `28b4831` runner evidence packet and oversized tool-result sidecar
   - decision: `already_covered`
   - owner_surface: `MDS runner / evidence packets`
   - local coverage: current main already has AI-first context budget telemetry, compact quest evidence packet cache, runtime tool-result delta compaction, runner tool budget caching, read telemetry persistence, artifact deltas, and progress-marker telemetry.

2. upstream `ef78200` / merge `eac31af` runtime log hygiene
   - decision: `already_covered_or_watch`
   - owner_surface: `MDS runtime storage / bash_exec`
   - local coverage: current main already has runtime storage compaction, cold payload archiving, log growth hygiene, and hot-path retention work. No new MDS slice was selected without a narrower compatibility gap.

3. upstream `f3a8262` / merge `d4fe0a2` runner diagnostics
   - decision: `already_covered`
   - owner_surface: `MDS runner diagnostics / daemon doctor`
   - local coverage: current main already has runtime failure taxonomy, provider failure handling, retry exhaustion diagnostics, and faster daemon resume / recovery surfaces.

### C. Watch Only

1. upstream `e7901cd` workspace explorer payload reduction
   - decision: `watch_only`
   - rationale: useful product/runtime-size idea, but current fork already attacks context pressure through evidence packets and delta compaction. Revisit only if workspace file tree payload becomes a real MAS/MDS compatibility cost.

2. upstream `242efa4` runner startup, doctor, and Kimi support
   - decision: `watch_only`
   - rationale: provider and startup-doc surfaces remain upstream product breadth. Current fork keeps provider diversity under Codex profile compatibility rather than expanding MDS product runner authority.

### D. Rejected / Deferred Product Surface

1. upstream `26d5d43`, `aea7c05`, `f20ce61`, `1e9eb34`, `10cb5cf`
   - decision: `reject_for_current_mds_mainline`
   - rationale: these are continuation notice, paper tool cards, onboarding, tooltip, and responsive settings UI changes. They do not strengthen the current `MedAutoScience -> MedDeepScientist` compatibility contract.

2. upstream `68776ed`, `1f042ef`
   - decision: `reject_or_docs_watch`
   - rationale: WeChat QR and provider setup docs are upstream product/operator documentation. They do not become MAS/MDS owner truth unless a concrete controlled-backend compatibility need appears.

## Outcome

This round did not bulk-sync upstream and did not cherry-pick MDS runtime code.

The useful learned slice is paper-quality planning discipline:

- separate paper-facing story from evidence/reproducibility facts
- make claim/evidence boundaries explicit before drafting
- treat reviewer objections and analysis-count adequacy as outline readiness signals
- prevent user/operator/runtime provenance from leaking into manuscript prose

The landing for this round is MAS-side contract/template intake plus meta-test coverage. A future MDS code slice should be narrow and callable, most likely around academic-outline validation or manuscript-language validation, only after a MAS consumer contract exists.

## Verification

MDS doc-only verification:

```bash
git diff --check
```

MAS verification is recorded in the paired MAS intake document.
