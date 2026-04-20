# 22 Windows + WSL2 部署指南

当操作机器是 Windows 10/11，并且你希望把运行时稳定地放在 WSL2 里的 Linux 环境中时，使用这份指南。

MedDeepScientist 目前保留了继承运行时的兼容名字：

- npm 包名：`@researai/deepscientist`
- 启动命令：`ds`
- WSL 内默认 home：`~/DeepScientist`

如果你希望 AI coding agent 直接执行安装或修复流程，请让它读取当前仓库里的 [`src/skills/windows-wsl2-setup/SKILL.md`](../../src/skills/windows-wsl2-setup/SKILL.md)。这份文档是给人的部署路径，skill 是给 agent 的可执行路径。

## 成功状态

在 WSL 内依次验证：

```bash
command -v node npm git uv codex ds
codex exec --skip-git-repo-check "Print exactly OK and exit."
ds doctor
```

然后启动运行时：

```bash
ds --here
```

再从 Windows 浏览器打开启动后打印出来的地址。默认本地地址是：

```text
http://127.0.0.1:20999
```

## 1. 准备 Windows 与 WSL2

在 Windows PowerShell 管理员窗口中执行：

```powershell
wsl --install -d Ubuntu
wsl --set-default-version 2
wsl -l -v
```

如果机器之前已经装过 WSL，也建议先检查 `wsl --status` 与 `wsl -l -v`，再进入 Linux 侧继续安装。

如果你希望把 Linux 镜像放到副盘，先完成标准的导出 / 导入迁移，再在新位置安装运行时工具。

## 2. 保持 Linux 工具全部在 WSL 内

进入发行版：

```powershell
wsl -d Ubuntu
```

在 WSL 内安装基础工具，并关闭 Windows PATH 注入：

```bash
sudo apt update
sudo apt install -y build-essential curl git ca-certificates
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[interop]
appendWindowsPath=false
EOF
exit
```

回到 Windows PowerShell：

```powershell
wsl --terminate Ubuntu
wsl -d Ubuntu
```

这样重新进入后，`appendWindowsPath=false` 才会真正生效。之后所有工具检查都应该解析到 WSL 内的 Linux 路径。

## 3. 安装 Node.js，并把 npm 全局写入放到用户目录

在 WSL 内执行：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
grep -qxF 'export PATH="$HOME/.npm-global/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
node --version
npm --version
```

任何满足仓库最低要求的 Node LTS 都可以。关键点是 `node`、`npm` 都来自 WSL 内部，而且全局 npm 安装不需要 `sudo`。

## 4. 安装 `ds`、`codex` 与 `uv`

先安装运行时包：

```bash
npm install -g @researai/deepscientist
```

DeepScientist 通常会从这次安装里一并拿到 bundled Codex 依赖。验证：

```bash
command -v codex
command -v ds
ds --version
```

如果 `codex` 仍然不存在，再显式安装一次：

```bash
npm install -g @openai/codex
```

安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version
```

## 5. 在第一次运行 `ds` 之前完成 Codex 配置

使用以下两条受支持路径之一。

### 5.1 默认 OpenAI 登录路径

```bash
codex --login
```

如果你本机的 Codex 版本通过 `codex` 本身进入交互式初始化，就直接使用那个入口。

### 5.2 provider-backed profile 路径

如果你已经在本机使用 `m27`、`glm`、`ark`、`bailian` 这类 profile，先验证：

```bash
codex --profile m27
```

然后让 DeepScientist 复用同一个 profile：

```bash
ds doctor --codex-profile m27
ds --codex-profile m27
```

provider 细节继续看 [15 Codex Provider 配置](./15_CODEX_PROVIDER_SETUP.md)。

## 6. 运行诊断并启动运行时

在 WSL 内执行：

```bash
ds doctor
```

如果你走的是 provider-backed profile：

```bash
ds doctor --codex-profile m27
```

使用项目局部 home：

```bash
mkdir -p ~/projects/ds-demo
cd ~/projects/ds-demo
ds --here
```

使用默认 home：

```bash
ds
```

## 7. 浏览器访问与 launcher 说明

启动后，直接从 Windows 侧的 Chrome、Edge 或其他浏览器打开打印出来的本地 URL。

如果你需要显式绑定 daemon 地址，使用 `--host`：

```bash
ds --host 0.0.0.0 --port 20999
```

旧脚本里如果还在传 `--ip`，launcher 现在会继续兼容，但会打印迁移提示，并把它映射成 `--host`。即使绑定地址是 `0.0.0.0`，本机浏览器访问仍然使用 `127.0.0.1`。

## 8. 常见失败模式

### WSL 无法正常启动

- 在 PowerShell 中检查 `wsl --status` 与 `wsl -l -v`
- 如果遇到 `HCS_E_CONNECTION_TIMEOUT` 或 Hyper-V 启动类错误，先完成 Windows 更新并重启，再继续

### `codex` 在某个 shell 能用，但 `ds doctor` 失败

- 在同一个 WSL shell 里重跑完全相同的 profile
- 如果可用的 `codex` 不在 `PATH` 上，用 `--codex /absolute/path/to/codex` 显式指定
- 回看 [15 Codex Provider 配置](./15_CODEX_PROVIDER_SETUP.md) 里的 profile 环境变量和 endpoint 形状

### `uv` 运行时同步失败

launcher 在 `uv` 原始报错后面会追加诊断提示，真正的根因仍然以上面那段 `uv` 输出为准。最常见的本地干扰面有三类：

- 活跃的 Python 环境，例如 `VIRTUAL_ENV`、`CONDA_PREFIX`、`PYTHONPATH`、`PYTHONHOME`
- 自定义包索引，例如 `PIP_*`、`UV_INDEX_URL`、`UV_EXTRA_INDEX_URL`
- 代理或证书覆盖，例如 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`SSL_CERT_FILE`、`REQUESTS_CA_BUNDLE`

最快的修复路径：

```bash
deactivate 2>/dev/null || true
conda deactivate 2>/dev/null || true
env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV -u CONDA_PREFIX ds doctor
```

然后再执行 `ds`。如果你当前运行的是源码 checkout，还可能需要：

```bash
uv lock
```

### `20999` 端口被占用

```bash
ds --status
ds --stop
```

或者改端口启动：

```bash
ds --port 21000
```

## 9. 相关文档

- [00 快速开始](./00_QUICK_START.md)
- [09 启动诊断](./09_DOCTOR.md)
- [15 Codex Provider 配置](./15_CODEX_PROVIDER_SETUP.md)
- [Windows WSL2 安装 skill](../../src/skills/windows-wsl2-setup/SKILL.md)
