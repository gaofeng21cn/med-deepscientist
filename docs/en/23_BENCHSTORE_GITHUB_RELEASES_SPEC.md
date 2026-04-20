# 23 BenchStore GitHub Releases Spec

This document defines the recommended release and distribution contract for BenchStore
benchmark source packages when the delivery backend is GitHub Releases.

In the current MedDeepScientist fork, this is a maintainer-facing packaging spec. The
stable runtime surface today is still the read-only catalog plus setup packet flow. This
spec matters because it keeps source bundles deterministic, auditable, and ready for a
future explicit install lane.

Related document:

- [22 BenchStore YAML Authoring Guide](./22_BENCHSTORE_YAML_REFERENCE.md)

## 1. Scope

This spec applies to benchmark source packages that:

- are listed in `AISB/catalog/*.yaml`
- are intended to be distributed as standalone source bundles
- use GitHub Release assets as the authoritative downloadable package

This spec does not require datasets, checkpoints, or credentials to be bundled into the same asset.

## 2. Release model

Recommended model:

- use one GitHub repository as the release host
- publish many benchmark zip files into one benchmark-assets release
- include one machine-readable `manifest.json` in the same release

Recommended repository host:

- the repository that owns and audits the published benchmark source bundles

Recommended release tag style:

- `benchstore-assets-2026-04-20`
- `benchstore-assets-r1`
- `benchstore-assets-2026q2`

Keep benchmark asset cadence separate from ordinary application version tags whenever possible.

## 3. Asset granularity

Each benchmark should remain an independent archive asset.

Recommended asset naming rule:

- `<benchmark_id>-v<package_version>.zip`

Examples:

- `aisb.t3.001_savvy-v0.1.0.zip`
- `aisb.t3.048_proxyspex-v0.1.0.zip`

Why:

- one benchmark can be updated without rebuilding every other benchmark
- one catalog entry maps to one asset deterministically
- checksums and install records stay benchmark-specific

## 4. Manifest requirement

Each benchmark-assets release should contain:

- benchmark zip assets
- one `manifest.json`

Recommended `manifest.json` shape:

```json
{
  "schema_version": 1,
  "release_id": "benchstore-assets-2026-04-20",
  "published_at": "2026-04-20T00:00:00Z",
  "repo": "example/benchstore-assets",
  "assets": [
    {
      "benchmark_id": "aisb.t3.001_savvy",
      "version": "0.1.0",
      "asset_name": "aisb.t3.001_savvy-v0.1.0.zip",
      "archive_type": "zip",
      "sha256": "<sha256>",
      "size_bytes": 12345678,
      "published_at": "2026-04-20T00:00:00Z"
    }
  ]
}
```

The manifest is useful even before a full install UI exists because it provides one
durable source of truth for:

- integrity verification
- bulk updates
- release audits
- later install-path expansion

## 5. What a benchmark archive should contain

A release asset should contain only the source package needed for benchmark installation
and later quest-local use.

It should usually contain:

- source code
- README and install notes
- requirements / pyproject / package metadata
- benchmark-local configs and scripts
- small benchmark-owned support files that are legal to redistribute

It should usually not contain:

- datasets
- model checkpoints unless redistribution is clearly allowed
- API secrets, auth files, cookies, or tokens
- generated logs, caches, outputs, or user-specific artifacts
- local machine absolute paths
- `.git`, `.ds`, `.codex`, `node_modules`, `dist`, `build`, `__pycache__`, `.pytest_cache`, `wandb`

## 6. Release-safe packaging rules

Before publishing a benchmark archive, the packager should:

1. copy from a curated local source snapshot, not from a live quest worktree with unknown transient state
2. remove generated artifacts and local runtime residue
3. remove secrets and workstation-specific auth material
4. preserve upstream source identity where legally possible
5. keep the archive root deterministic
6. compute and record `sha256`

Recommended archive root layout:

- archive root directory name should match `download.local_dir_name`

## 7. YAML contract for GitHub Releases

Recommended YAML contract:

```yaml
download:
  provider: github_release
  repo: example/benchstore-assets
  tag: benchstore-assets-2026-04-20
  asset_name: aisb.t3.048_proxyspex-v0.1.0.zip
  url: https://github.com/example/benchstore-assets/releases/download/benchstore-assets-2026-04-20/aisb.t3.048_proxyspex-v0.1.0.zip
  archive_type: zip
  local_dir_name: aisb.t3.048_proxyspex
  version: 0.1.0
  sha256: <sha256>
  size_bytes: 12345678
  published_at: 2026-04-20T00:00:00Z
  source_repo: https://github.com/example/upstream-benchmark
  source_commit: <git_commit_sha>
```

Rules:

- `download.url` should point to a concrete immutable release asset, not a moving branch archive
- `download.archive_type` should match the real asset type
- `download.local_dir_name` should match the expected unpacked root directory
- `download.sha256` should be provided for public release assets
- `download.provider` should be `github_release` for this mode

## 8. Paper, source package, and data should stay separate

Keep these separate:

- `paper.url`: paper or benchmark paper link
- `download.*`: benchmark source package link
- `dataset_download.*`: dataset acquisition route
- `credential_requirements.*`: tokens or API keys needed later

Do not overload one field with another asset type.

## 9. Versioning rules

`version` should be treated as the BenchStore package version, not necessarily the paper
version and not necessarily the upstream repository tag.

Bump the package version when:

- packaged source contents change
- release-safe cleanup changes the public archive contents
- bundled configs or install-critical files change

## 10. Current fork boundary

MedDeepScientist currently documents this release contract ahead of a wider BenchStore
install product surface.

That means:

- catalog entries may already include `download.*`
- maintainers should keep the release metadata deterministic now
- future install-path work should reuse this contract rather than invent a new one
