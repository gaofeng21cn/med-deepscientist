# 23 BenchStore GitHub Releases 分发规范

这份文档定义当 BenchStore benchmark 源码包通过 GitHub Releases 分发时，推荐遵守的发布与分发约束。

在当前 MedDeepScientist fork 里，这还是一份维护者导向的 packaging spec。当前稳定 runtime surface 仍然是 read-only catalog 加 setup packet 流程。之所以现在就写清楚，是为了让源码包从一开始就保持确定性、可审计，也为后续显式安装链路预留稳定合同。

相关文档：

- [22 BenchStore YAML 编写指南](./22_BENCHSTORE_YAML_REFERENCE.md)

## 1. 适用范围

本规范适用于：

- 被 `AISB/catalog/*.yaml` 引用的 benchmark
- 计划以独立源码包形式分发的 benchmark
- 其权威下载后端为 GitHub Release assets 的场景

本规范不要求把数据集、模型权重或凭据一起打包。

## 2. Release 模型

推荐模型：

- 用一个 GitHub 仓库承载 release 资产
- 在同一个 benchmark-assets release 下发布多个 benchmark zip
- 同时放一个机器可读的 `manifest.json`

推荐 tag 形式：

- `benchstore-assets-2026-04-20`
- `benchstore-assets-r1`
- `benchstore-assets-2026q2`

尽量把 benchmark 资产节奏和普通程序版本 tag 分开。

## 3. 资产粒度

每个 benchmark 都应保持为独立 archive asset。

推荐命名规则：

- `<benchmark_id>-v<package_version>.zip`

例如：

- `aisb.t3.001_savvy-v0.1.0.zip`
- `aisb.t3.048_proxyspex-v0.1.0.zip`

原因：

- 某一个 benchmark 可以单独更新
- 一个 catalog entry 能稳定映射到一个 asset
- checksum 和安装记录保持 benchmark 粒度

## 4. Manifest 要求

每个 benchmark-assets release 推荐包含：

- benchmark zip 资产
- 一个 `manifest.json`

推荐结构：

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

即使完整安装 UI 还没落地，manifest 现在也有价值，因为它能作为：

- 完整性校验依据
- 批量更新依据
- 发布审计依据
- 未来安装路径扩展的稳定基础

## 5. Benchmark archive 应包含什么

release asset 应只包含 benchmark 安装和 quest-local 使用真正需要的源码包。

通常应该包含：

- 源码
- README 和安装说明
- requirements / pyproject / package 元数据
- benchmark 自己的配置和脚本
- 可以合法分发的小型辅助资源

通常不应包含：

- 数据集
- 模型权重，除非明确允许再分发
- API secret、auth 文件、cookie、token
- 生成日志、缓存、输出物、用户本地临时产物
- 本地绝对路径
- `.git`、`.ds`、`.codex`、`node_modules`、`dist`、`build`、`__pycache__`、`.pytest_cache`、`wandb`

## 6. Release-safe 打包规则

发布前建议做到：

1. 从整理好的本地源码快照复制，而不是从带未知临时状态的 live quest worktree 直接打包
2. 删除生成产物和本地运行残留
3. 删除 secret 与本地认证材料
4. 在法律允许范围内保留上游源码身份
5. 保证 archive 根目录稳定
6. 计算并记录 `sha256`

推荐 archive 根目录规则：

- archive 解压后的根目录名应和 `download.local_dir_name` 一致

## 7. GitHub Releases 模式下的 YAML 合同

推荐写法：

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

规则：

- `download.url` 应指向具体不可变的 release asset，不能指向漂移的分支压缩包
- `download.archive_type` 应与真实资产类型一致
- `download.local_dir_name` 应与解压根目录一致
- 公开 release asset 建议填写 `download.sha256`
- GitHub Releases 模式下，`download.provider` 应写 `github_release`

## 8. 论文、源码包、数据要分开

这些字段应分别承载各自语义：

- `paper.url`：论文链接
- `download.*`：源码包链接
- `dataset_download.*`：数据集获取路径
- `credential_requirements.*`：后续需要的 token / key

一个字段只承载一种资产语义。

## 9. 版本规则

这里的 `version` 应理解为 BenchStore 源码包版本，不一定等于论文版本，也不一定等于上游仓库 tag。

以下情况需要 bump：

- 打包源码内容改变
- release-safe 清理改变，导致公开资产内容改变
- 打包时附带的配置或安装关键文件改变

## 10. 当前 fork 的边界

MedDeepScientist 现在先把这份 release contract 文档化，再逐步扩到更宽的 BenchStore 安装产品面。

这意味着：

- catalog entry 现在已经可以携带 `download.*`
- 维护者现在就应该保证 release metadata 的确定性
- 未来安装链路应该复用这份合同，而不是再发明一套新语义
