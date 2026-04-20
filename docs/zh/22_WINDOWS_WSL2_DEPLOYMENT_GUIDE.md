# 22 Windows WSL2 部署指南

这份指南给当前 MedDeepScientist fork 提供一条稳定的 Windows operator path。推荐形态很直接：在 WSL2 里运行 `ds`，把运行时工具链留在 Linux 侧，先验证 Codex，再启动本地 UI，最后从 Windows 浏览器访问。

## Truth sources

遇到行为细节需要确认时，按这个顺序回到仓库文档：

1. `README.md`
2. [00 快速开始](./00_QUICK_START.md)
3. [15 Codex Provider 配置](./15_CODEX_PROVIDER_SETUP.md)
4. [09 启动诊断](./09_DOCTOR.md)
5. [`src/skills/windows-wsl2-setup/SKILL.md`](../../src/skills/windows-wsl2-setup/SKILL.md)

这份指南负责把上面这些 repo 真相整理成一条 Windows 专用 workflow。命令细节有漂移时，以上文档继续作为权威入口。

## 完成标准

下面这些检查按顺序全部通过，才算真正装好：

1. 在 Windows 侧执行 `wsl -l -v`、`wsl --status`、`wsl -d <distro> -- echo hello` 都成功。
2. 在 WSL 里执行 `command -v node npm git uv codex ds`，结果都指向 Linux 路径。
3. 在 WSL 里执行 `codex exec --skip-git-repo-check "Print exactly OK and exit."` 成功。
4. `ds doctor` 能确认 Codex 路径健康。
5. `ds` 能在 WSL 中启动，Windows 浏览器能打开 `http://127.0.0.1:20999`。

## 1. 先准备 Windows 和 WSL2

如果你想要最干净的启动 lane，优先准备一个专用的 Ubuntu WSL2 发行版。

在 Windows PowerShell 里运行：

```powershell
wsl -l -v
wsl --status
wsl -d Ubuntu -- echo hello
```

只要 distro 还没稳定启动，就先修 Windows / WSL 层。`HCS_E_CONNECTION_TIMEOUT`、待重启更新、Hyper-V 启动问题都属于这一层。

## 2. 把运行时二进制留在 Linux 侧

进入 WSL 后，先关闭 Windows PATH 注入，再开始信任 `command -v` 的结果：

```bash
printf '[interop]\nappendWindowsPath=false\n' | sudo tee /etc/wsl.conf
```

然后回到 PowerShell 终止并重新进入 distro：

```powershell
wsl --terminate Ubuntu
```

重新进入 WSL 后，安装基础包、当前 Node LTS，以及用户目录下的 npm prefix：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git sudo build-essential python3-venv python3-pip

mkdir -p "$HOME/.npm-global" "$HOME/.local/bin"
npm config set prefix "$HOME/.npm-global"
printf '\nexport PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
printf '\nexport PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"\n' >> "$HOME/.profile"
source "$HOME/.bashrc"
```

把运行时工具链安装到 WSL 里：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
npm install -g @openai/codex
npm install -g @researai/deepscientist
```

如果你的环境已经依赖某个 provider 兼容版本或 wrapper，请把版本选择放回 [15 Codex Provider 配置](./15_CODEX_PROVIDER_SETUP.md)。这份指南刻意保持 launcher 路径不绑定固定版本。

## 3. 在 `ds` 之前先把 Codex 跑通

先在 WSL 里确认一条可用的 Codex 路径，再启动 `ds`：

### 默认登录路径

```bash
codex --login
```

如果当前 CLI 没有 `--login`，直接运行 `codex`，在交互界面里完成登录。

### provider-backed profile 路径

```bash
codex --profile <profile-name>
```

后续启动 DeepScientist 时沿用同一个 profile：

```bash
ds --codex-profile <profile-name>
```

当前 fork 会默认继承你本机 Codex 的默认模型和默认推理设置，只有你显式覆盖时才改。`--codex-profile` 负责选一轮 profile，`--codex` 负责指定一轮可执行文件。

## 4. 按顺序验证

在 WSL 里运行：

```bash
whoami
command -v node npm git uv codex ds
codex exec --skip-git-repo-check "Print exactly OK and exit."
ds doctor
```

如果你走 provider-backed profile，`doctor` 也带上同一个 profile：

```bash
ds doctor --codex-profile <profile-name>
```

只有 `codex exec` 和 `ds doctor` 都健康，才继续下一步。

## 5. 启动运行时并从 Windows 打开

先进入 WSL 里的工作目录：

```bash
mkdir -p ~/deepscientist-work
cd ~/deepscientist-work
ds --here
```

如果你要带 profile：

```bash
ds --here --codex-profile <profile-name>
```

稳定的本地浏览器地址是：

```text
http://127.0.0.1:20999
```

当你需要 daemon 绑定所有网卡时，可以使用 `--host 0.0.0.0`。本地浏览器入口依然是 `127.0.0.1`。`--ip` 依然兼容可用，但它已经进入迁移阶段，当前 flag 是 `--host`。

## 6. 代理与网络说明

先在 WSL 里测试直连，再决定要不要持久化代理变量：

```bash
curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://chatgpt.com/
curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://github.com/
```

如果确实需要 Windows 侧代理，先在 PowerShell 中查看候选监听端口：

```powershell
pwsh -File scripts/find-wsl-proxy.ps1
```

然后先用 WSL 默认网关测试通路，确认可达后再落持久化环境变量。

## 7. 常见修复路径

| 现象 | 检查方向 |
|---|---|
| `command -v codex` 或 `ds` 指向 `/mnt/c/...` | 回头检查 `/etc/wsl.conf`，终止 distro 后重新验证 |
| `codex exec` 失败 | 先修登录、profile 或 provider 配置，再打开 `ds` |
| `ds doctor` 卡在 uv bootstrap 或 sync | 先读 uv 原始报错，再检查 `VIRTUAL_ENV`、`CONDA_PREFIX`、`PYTHONPATH`、`PYTHONHOME`、`PIP_*`、`UV_INDEX_URL`、`UV_EXTRA_INDEX_URL`、`HTTP(S)_PROXY`、`SSL_CERT_FILE`、`REQUESTS_CA_BUNDLE` |
| source checkout 改过 Python 依赖后 uv sync 失败 | 先执行 `uv lock`，再重试 |
| npm 安装版 uv sync 失败 | 优先排查本地 Python、代理、证书或包索引配置；npm 包本身已经带有锁定的 `uv.lock` |
| Windows 浏览器打不开 `127.0.0.1:20999` | 保持 WSL 里的 `ds` 进程存活，再检查防火墙、代理和 WSL 网络状态 |

## 相关文档

- [00 快速开始](./00_QUICK_START.md)
- [09 启动诊断](./09_DOCTOR.md)
- [15 Codex Provider 配置](./15_CODEX_PROVIDER_SETUP.md)
- [`src/skills/windows-wsl2-setup/SKILL.md`](../../src/skills/windows-wsl2-setup/SKILL.md)
