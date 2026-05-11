# MDS test retirement boundary

Owner: `MedDeepScientist maintainers`
Purpose: record the current testing boundary after the MAS functional monolith closeout
State: `current reference`
Machine boundary: human reference only; tests must assert structured runtime, schema, contract, CLI/API, generated artifact, or guard surfaces instead

`MedDeepScientist` is now a frozen archive, historical fixture, explicit legacy diagnostic target, and upstream intake reference for MAS-owned behavior. Tests should preserve that role without promoting MDS back into a default product/runtime owner.

Keep tests for:

- runtime protocol routes, request/response keys, startup/turn contract, quest layout, artifact layout, and event surfaces
- schema and registry guards, including strangler and owner-reflux checks
- CLI/API behavior that remains part of fork-local diagnostic operation
- generated artifact structure and pollution/hygiene guards
- archive/reference fixtures that compare legacy behavior without granting product authority

Retire or rewrite tests that:

- assert exact `README*`, `docs/**`, guide, or Markdown prose wording
- pin `SKILL.md` body text when file existence, sync behavior, or structured callable/artifact contract is enough
- require old active product, daemon, WebUI, OPL active-domain, or MAS default-runtime semantics
- treat MDS `paper_contract_health`, coverage, prompt prose, or skill wording as medical publication quality authority
- use repo doc paths as machine contracts instead of structured surfaces, policy IDs, schemas, or reports

Narrative docs may still be linked with `human_doc:*` identifiers or used as maintainer context. They are not compatibility contracts.
