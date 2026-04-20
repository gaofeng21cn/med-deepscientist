# 22 BenchStore YAML Authoring Guide

This guide explains how to add or maintain a BenchStore catalog entry under `AISB/catalog/`,
how auto-discovery works in the current MedDeepScientist fork, and which fields are
actually consumed today.

This fork currently treats BenchStore as a maintainer-facing catalog surface with three
stable capabilities:

- catalog entry normalization and validation
- catalog listing / entry lookup / query filtering
- setup packet generation for the controlled `catalog -> setup packet -> Start Research / SetupAgent` path

This fork does not yet treat a productized BenchStore download UI as a stable public
surface. Authoring and release metadata are still valuable because they shape catalog
quality now and keep future package distribution deterministic.

For source-bundle packaging through GitHub Releases, see
[23 BenchStore GitHub Releases Spec](./23_BENCHSTORE_GITHUB_RELEASES_SPEC.md).

## 1. How auto-discovery works

BenchStore does not use a manual registry.

If you add a YAML file under `AISB/catalog/`, BenchStore will pick it up automatically
on the next catalog scan.

Current rules:

- BenchStore scans `AISB/catalog/**/*.yaml` recursively.
- One YAML file represents one entry.
- `name` is the only strictly required field.
- `id` is optional. If omitted, BenchStore derives it from the file stem.
- Entry ids must be unique across the whole catalog.
- Files ending in `.zh.yaml` are locale-specific variants for Chinese surfaces.
- When locale is `zh`, BenchStore prefers `<stem>.zh.yaml` over `<stem>.yaml`.
- The `.zh.yaml` file is a full replacement, not a field-level merge.

Examples:

- `AISB/catalog/my.benchmark.yaml`
- `AISB/catalog/my.benchmark.zh.yaml`
- `AISB/catalog/vision/my.benchmark.yaml`

Recommended naming rule:

- Keep the file stem identical to the intended entry id.
- Use only letters, numbers, `.`, `_`, and `-` in the stem.

## 2. Quick start: create a new YAML entry

### Minimal entry

This is the smallest valid file:

```yaml
name: My Benchmark
```

That entry will appear in BenchStore, but it will be minimal and weak for filtering,
ranking, and setup assistance.

### Recommended starter template

Use this as the normal starting point:

```yaml
schema_version: 1
id: my.benchmark
name: My Benchmark
version: 0.1.0

one_line: One-sentence summary shown in cards and compact views.
task_description: >
  A longer description used by the detail view and setup packet flow.

task_mode: evaluation_driven
requires_execution: true
requires_paper: true

capability_tags:
  - scientific_discovery
track_fit:
  - benchmark_track

time_band: 1-2h
cost_band: medium
difficulty: medium
data_access: public

snapshot_status: runnable
support_level: advanced

resources:
  minimum:
    cpu_cores: 8
    ram_gb: 16
    disk_gb: 50
    gpu_count: 1
    gpu_vram_gb: 12
  recommended:
    cpu_cores: 16
    ram_gb: 32
    disk_gb: 100
    gpu_count: 1
    gpu_vram_gb: 24

paper:
  title: My Benchmark Paper
  venue: NeurIPS 2026
  year: 2026
  url: https://example.com/paper

download:
  url: https://example.com/my.benchmark.zip
  archive_type: zip
  local_dir_name: my.benchmark

image_path: ../../../AISB/image/my.benchmark.jpg
```

### Chinese localization

If you want a Chinese catalog entry, create a second file with the same stem:

- `AISB/catalog/my.benchmark.yaml`
- `AISB/catalog/my.benchmark.zh.yaml`

Important:

- `my.benchmark.zh.yaml` must contain a complete entry.
- BenchStore does not merge the Chinese file onto the English file.
- If you only put translated fragments into `.zh.yaml`, missing fields will really be missing.

## 3. Exact requirements and conventions

### 3.1 Hard requirements

The following are hard requirements or hard runtime behaviors in the current implementation:

- The YAML root must be an object, not a plain string or list.
- `name` must be a non-empty string.
- If `id` is present, it should be a string. If omitted, BenchStore derives it from the file stem.
- The final resolved `id` must be unique across the whole catalog.
- `.zh.yaml` fully replaces the matching English file. It is not merged field-by-field.
- `capability_tags`, `track_fit`, `primary_outputs`, `environment.key_packages`, `environment.notes`, `dataset_download.notes`, `credential_requirements.items`, and `credential_requirements.notes` must be lists.
- If present, `resources.minimum` and `resources.recommended` must be objects.
- If present, `environment`, `dataset_download`, `credential_requirements`, `paper`, and `download` must be objects.

Current fork note:

- `download.*` is catalog metadata in the current fork. It is useful for release packaging and future deterministic install paths, but the current stable runtime contract is still the read-only catalog plus setup packet surface.

### 3.2 Recommended conventions

These are not strict validator rules, but they keep catalog behavior predictable and low-maintenance.

**Base conventions**

- `schema_version`: always write `1`.
- `id`: make it identical to the file stem. For example, if the file is `aisb.t3.026_gartkg.yaml`, write `id: aisb.t3.026_gartkg`.
- `id` style: prefer lowercase, stable identifiers, using only letters, numbers, `.`, `_`, and `-`.
- `version`: prefer semver such as `0.1.0` or `0.2.3`.
- `requires_execution` and `requires_paper`: write YAML booleans `true` / `false`, not natural-language strings.

**Writing conventions**

- `name`: primary user-facing title; prefer the official benchmark or project name.
- `one_line`: one sentence suitable for a card.
- `task_description`: usually 1 to 3 paragraphs describing what the benchmark means inside the local MedDeepScientist / MedAutoScience workflow, not just a copied abstract.
- `recommended_when` / `not_recommended_when`: write complete fit-condition sentences if you use them.

**Canonical values recognized by recommendation logic**

- `cost_band`: prefer only `very_low`, `low`, `medium`, `high`, `very_high`.
- `difficulty`: prefer only `easy`, `medium`, `hard`, `expert`.
- `data_access`: prefer only `public`, `restricted`, `private`.
- `snapshot_status`: prefer only `runnable`, `runnable_not_verified`, `partial`, `restore_needed`, `external_eval_required`, `data_only`.
- `support_level`: prefer only `turnkey`, `advanced`, `recovery`.

Important:

- These are not hard-enforced enums.
- If you write another string, the entry will still load, but recommendation behavior will usually fall back to unknown/default handling.

**`time_band` format**

BenchStore currently parses these formats reliably:

- single value: `30m`, `2h`, `3d`
- closed range: `30-60m`, `1-2h`, `2-4d`
- open-ended range: `6h+`, `1d+`, `4d+`

Guidance:

- estimate the first credible end-to-end wall-clock run
- prefer normalized no-space forms like `1-2h`

**Resource conventions**

Inside `resources.minimum` and `resources.recommended`, BenchStore currently reads only these five numeric keys:

- `cpu_cores`
- `ram_gb`
- `disk_gb`
- `gpu_count`
- `gpu_vram_gb`

**Download conventions**

- `download.url`: recommended when the benchmark has a maintained source package or release asset.
- `download.archive_type`: prefer only `zip`, `tar.gz`, or `tar`.
- `download.local_dir_name`: make it match the unpacked root directory; in most cases it should also match the entry id.
- For GitHub Releases distribution, also fill `download.provider`, `download.repo`, `download.tag`, `download.asset_name`, `download.sha256`, and `download.size_bytes`.

**Image and localization conventions**

- `image_path`: prefer a path relative to the YAML file; the resolved file must exist and stay inside the current workspace.
- `.zh.yaml`: duplicate the full English entry first, then translate only the text-bearing fields.

## 4. What to fill, by outcome

### Enough to show up in BenchStore

Required:

- `name`

Strongly recommended:

- `id`
- `one_line`
- `task_description`

### Enough to rank, filter, and recommend well

These fields materially affect catalog quality:

- `task_mode`
- `capability_tags`
- `track_fit`
- `cost_band`
- `time_band`
- `difficulty`
- `data_access`
- `resources.minimum`
- `resources.recommended`
- `snapshot_status`
- `support_level`

### Enough to support setup packet generation well

These fields materially improve the current setup packet path:

- `one_line`
- `task_description`
- `requires_execution`
- `requires_paper`
- `paper.url`
- `dataset_download.sources`
- `download.url`
- `resources.minimum`
- `resources.recommended`

### Enough to support future release packaging cleanly

Recommended:

- `download.url`
- `download.archive_type`
- `download.local_dir_name`
- `version`
- `download.sha256`
- `download.size_bytes`

## 5. Source of truth in this fork

When in doubt, follow the implementation:

- loader and schema normalization: `src/deepscientist/benchstore/loader.py`
- catalog query and setup packet logic: `src/deepscientist/benchstore/service.py`
- focused tests: `tests/test_benchstore_registry.py`, `tests/test_benchstore.py`

If this guide and code ever drift, update the guide together with the implementation and tests.
