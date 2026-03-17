# DeepScientist

<p align="center">
  <img src="assets/branding/logo.svg" alt="DeepScientist logo" width="120" />
</p>

<p align="center">
  Local-first research operating system with a Python runtime, an npm launcher,
  one quest per Git repository, and shared web plus TUI surfaces.
</p>

## Install

Install `uv` first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install DeepScientist and Codex:

```bash
npm install -g @openai/codex @researai/deepscientist
```

## Start

```bash
ds
```

DeepScientist starts the local web workspace at `http://127.0.0.1:20999` by default.

If you want another port:

```bash
ds --port 21000
```

If you want to bind on all interfaces:

```bash
ds --host 0.0.0.0 --port 21000
```

DeepScientist now uses `uv` to manage a locked local Python runtime. If a conda environment is active and already provides Python `>=3.11`, `ds` prefers it automatically; otherwise `uv` provisions a managed Python toolchain under `~/DeepScientist/runtime/python/` and a locked environment under `~/DeepScientist/runtime/python-env/`.

The default DeepScientist home is:

- macOS / Linux: `~/DeepScientist`
- Windows: `%USERPROFILE%\\DeepScientist`

Use `ds --home <path>` if you want to place the runtime somewhere else.

## Troubleshooting

```bash
ds doctor
```

`ds docker` is also accepted as a compatibility alias, but `ds doctor` is the documented command.

## Local PDF Compile

```bash
ds latex install-runtime
```

This installs a lightweight TinyTeX `pdflatex` runtime for local paper compilation.

## QQ Connector

- [Quick Start (English)](docs/en/00_QUICK_START.md)
- [快速开始（中文）](docs/zh/00_QUICK_START.md)
- [QQ Connector Guide (English)](docs/en/03_QQ_CONNECTOR_GUIDE.md)
- [QQ Connector Guide (中文)](docs/zh/03_QQ_CONNECTOR_GUIDE.md)

## Maintainers

- [Architecture](docs/en/90_ARCHITECTURE.md)
- [Development Guide](docs/en/91_DEVELOPMENT.md)

## Citation

This project is currently contributed by Yixuan Weng, Shichen Li, Weixu Zhao, Minjun Zhu. If you find our work valuable, please cite:

本项目当前由 Yixuan Weng、Shichen Li、Weixu Zhao、Minjun Zhu 共同贡献。如果你觉得我们的工作有价值，请引用：

```bibtex
@inproceedings{
weng2026deepscientist,
title={DeepScientist: Advancing Frontier-Pushing Scientific Findings Progressively},
author={Yixuan Weng and Minjun Zhu and Qiujie Xie and QiYao Sun and Zhen Lin and Sifan Liu and Yue Zhang},
booktitle={The Fourteenth International Conference on Learning Representations},
year={2026},
url={https://openreview.net/forum?id=cZFgsLq8Gs}
}
```

## License

[MIT](LICENSE)
