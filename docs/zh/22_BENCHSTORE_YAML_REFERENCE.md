# 22 BenchStore YAML 编写指南

这份文档说明如何在 `AISB/catalog/` 下新增或维护 BenchStore 条目、当前 MedDeepScientist fork 的自动发现规则，以及当前实现真正会读取哪些字段。

这个 fork 目前把 BenchStore 视为一个维护者导向的 catalog surface，稳定能力有三类：

- catalog 条目正常化与校验
- catalog 列表 / 单项读取 / 查询过滤
- 受控 `catalog -> setup packet -> Start Research / SetupAgent` 路径下的 setup packet 生成

当前 fork 还没有把产品化的 BenchStore 下载 UI 视为稳定 public surface。即便如此，authoring 字段和 release 元数据现在依然有价值，因为它们已经影响 catalog 质量，也能为后续确定性源码包分发留出稳定约束。

如果要通过 GitHub Releases 分发 benchmark 源码包，请同时看
[23 BenchStore GitHub Releases 分发规范](./23_BENCHSTORE_GITHUB_RELEASES_SPEC.md)。

## 1. 自动发现规则

BenchStore 不需要手工注册表。

只要把 YAML 文件放进 `AISB/catalog/`，BenchStore 下一次扫描 catalog 时就会自动读到。

当前规则：

- BenchStore 递归扫描 `AISB/catalog/**/*.yaml`。
- 一个 YAML 文件对应一个条目。
- `name` 是唯一严格必填字段。
- `id` 可以不写；不写时会自动回退成文件名 stem。
- 整个 catalog 内的 `id` 必须唯一。
- 以 `.zh.yaml` 结尾的文件是中文本地化版本。
- 当 locale 是 `zh` 时，BenchStore 会优先读取 `<stem>.zh.yaml`。
- `.zh.yaml` 是完整替换，不做字段级 merge。

例如：

- `AISB/catalog/my.benchmark.yaml`
- `AISB/catalog/my.benchmark.zh.yaml`
- `AISB/catalog/vision/my.benchmark.yaml`

推荐命名规则：

- 文件名 stem 直接等于你想要的 entry id。
- stem 尽量只用字母、数字、`.`、`_`、`-`。

## 2. 快速上手：新增一个 YAML

### 最小可用文件

最小合法内容：

```yaml
name: My Benchmark
```

它会出现在 BenchStore 里，但在过滤、推荐和 setup assist 里信息会非常弱。

### 推荐起步模板

通常建议从这个模板开始：

```yaml
schema_version: 1
id: my.benchmark
name: My Benchmark
version: 0.1.0

one_line: 卡片和概览里展示的一句话摘要。
task_description: >
  详情页和 setup packet 流程使用的较长描述。

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

### 中文本地化

如果要支持中文展示，就再加一个同 stem 的文件：

- `AISB/catalog/my.benchmark.yaml`
- `AISB/catalog/my.benchmark.zh.yaml`

重要提醒：

- `my.benchmark.zh.yaml` 必须是一份完整条目。
- BenchStore 不会把中文文件和英文文件做字段合并。
- 如果只在 `.zh.yaml` 里写几个翻译字段，其他字段就真的不存在。

## 3. 具体要求和建议

### 3.1 系统硬要求

下面这些属于当前实现层面的硬要求或硬行为：

- YAML 根节点必须是 object，不能是纯字符串或纯列表。
- `name` 必须是非空字符串。
- `id` 如果写了，应该是字符串；如果不写，会自动从文件名 stem 推导。
- 最终解析出来的 `id` 必须在整个 catalog 中唯一。
- `.zh.yaml` 会完整替换同 stem 的英文文件，不做字段级合并。
- `capability_tags`、`track_fit`、`primary_outputs`、`environment.key_packages`、`environment.notes`、`dataset_download.notes`、`credential_requirements.items`、`credential_requirements.notes` 必须写成列表。
- `resources.minimum` 和 `resources.recommended` 如果写了，必须是 object。
- `environment`、`dataset_download`、`credential_requirements`、`paper`、`download` 如果写了，必须是 object。

当前 fork 说明：

- `download.*` 在当前 fork 里主要是 catalog 元数据。它对 release packaging 和未来确定性安装路径有价值，但当前稳定 runtime contract 仍然是 read-only catalog 加 setup packet surface。

### 3.2 推荐填写规范

下面这些不是代码强校验，但按这个约定写，catalog 行为会更稳定。

**基础规范**

- `schema_version`：固定写 `1`。
- `id`：直接等于文件名 stem，例如 `aisb.t3.026_gartkg.yaml` 对应 `id: aisb.t3.026_gartkg`。
- `id` 风格：推荐全小写、稳定，只用字母、数字、`.`、`_`、`-`。
- `version`：推荐 semver，例如 `0.1.0`、`0.2.3`。
- `requires_execution`、`requires_paper`：用 YAML 布尔值 `true` / `false`。

**文案规范**

- `name`：主标题，优先使用 benchmark 或项目正式名字。
- `one_line`：一行摘要。
- `task_description`：建议 1 到 3 段，重点写这个 benchmark 在本地 MedDeepScientist / MedAutoScience 工作流里实际意味着什么。
- `recommended_when` / `not_recommended_when`：如果使用，写完整句子。

**推荐逻辑识别的标准值**

- `cost_band`：推荐只用 `very_low`、`low`、`medium`、`high`、`very_high`。
- `difficulty`：推荐只用 `easy`、`medium`、`hard`、`expert`。
- `data_access`：推荐只用 `public`、`restricted`、`private`。
- `snapshot_status`：推荐只用 `runnable`、`runnable_not_verified`、`partial`、`restore_needed`、`external_eval_required`、`data_only`。
- `support_level`：推荐只用 `turnkey`、`advanced`、`recovery`。

重要说明：

- 这些不是强枚举校验。
- 写别的字符串也能加载，只是推荐逻辑通常会退回未知值处理。

**`time_band` 格式**

BenchStore 当前能稳定识别这些格式：

- 单值：`30m`、`2h`、`3d`
- 区间：`30-60m`、`1-2h`、`2-4d`
- 开放区间：`6h+`、`1d+`、`4d+`

建议：

- 用第一次可信端到端运行的 wall-clock 估计
- 直接写 `1-2h` 这类无空格规范格式

**资源字段**

`resources.minimum` 和 `resources.recommended` 里，当前真正会读取的只有这 5 个数值键：

- `cpu_cores`
- `ram_gb`
- `disk_gb`
- `gpu_count`
- `gpu_vram_gb`

**下载字段**

- `download.url`：当 benchmark 维护了源码包或 release asset 时，推荐填写。
- `download.archive_type`：推荐只写 `zip`、`tar.gz`、`tar`。
- `download.local_dir_name`：推荐等于解压后的根目录名；通常也建议和 `id` 保持一致。
- 如果走 GitHub Releases 分发，再补 `download.provider`、`download.repo`、`download.tag`、`download.asset_name`、`download.sha256`、`download.size_bytes`。

**图片与本地化**

- `image_path`：推荐写相对于 YAML 文件的相对路径；解析后的文件必须真实存在，并仍位于当前 workspace 内。
- `.zh.yaml`：建议先完整复制英文条目，再翻译文案字段。

## 4. 按目标来看，需要填写哪些字段

### 只要能在 BenchStore 里出现

必填：

- `name`

强烈建议：

- `id`
- `one_line`
- `task_description`

### 想让推荐、过滤、排序更靠谱

这些字段会明显影响 catalog 质量：

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

### 想让当前 setup packet 路径更好用

这些字段会明显改善当前 setup packet 效果：

- `one_line`
- `task_description`
- `requires_execution`
- `requires_paper`
- `paper.url`
- `dataset_download.sources`
- `download.url`
- `resources.minimum`
- `resources.recommended`

### 想让未来 release packaging 更干净

推荐填写：

- `download.url`
- `download.archive_type`
- `download.local_dir_name`
- `version`
- `download.sha256`
- `download.size_bytes`

## 5. 当前 fork 的实现真相

有疑问时，以实现为准：

- loader 和 schema 正常化：`src/deepscientist/benchstore/loader.py`
- catalog query 和 setup packet：`src/deepscientist/benchstore/service.py`
- focused tests：`tests/test_benchstore_registry.py`、`tests/test_benchstore.py`

如果本文和代码发生漂移，需要一起更新文档、实现和测试。
