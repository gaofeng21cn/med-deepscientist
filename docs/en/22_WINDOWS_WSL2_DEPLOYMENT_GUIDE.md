# 22 Windows + WSL2 Deployment Guide

Use this guide when the operator machine is Windows 10/11 and the runtime should stay Linux-side inside WSL2.

MedDeepScientist keeps the compatibility launcher and package names from the inherited runtime:

- npm package: `@researai/deepscientist`
- launcher: `ds`
- default home inside WSL: `~/DeepScientist`

If an AI coding agent should execute the install or repair flow directly, point it at [`src/skills/windows-wsl2-setup/SKILL.md`](../../src/skills/windows-wsl2-setup/SKILL.md) in the current repo. This document is the human-readable deployment lane; the skill is the executable lane for agents.

## What success looks like

Run these checks inside WSL:

```bash
command -v node npm git uv codex ds
codex exec --skip-git-repo-check "Print exactly OK and exit."
ds doctor
```

Then start the runtime:

```bash
ds --here
```

Open the printed URL from the Windows browser. The default local URL is:

```text
http://127.0.0.1:20999
```

## 1. Prepare Windows and WSL2

In Windows PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu
wsl --set-default-version 2
wsl -l -v
```

If WSL was already installed earlier, still verify `wsl --status` and `wsl -l -v` before touching the Linux side.

If your machine keeps large Linux images on a secondary drive, move the distro with the standard export/import flow before installing tools inside it.

## 2. Keep Linux tools Linux-side

Enter the distro:

```powershell
wsl -d Ubuntu
```

Inside WSL, install the baseline packages and keep Windows binaries out of the execution path:

```bash
sudo apt update
sudo apt install -y build-essential curl git ca-certificates
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[interop]
appendWindowsPath=false
EOF
exit
```

Back in Windows PowerShell:

```powershell
wsl --terminate Ubuntu
wsl -d Ubuntu
```

That restart makes `appendWindowsPath=false` take effect. After you re-enter WSL, every tool check should resolve to Linux paths.

## 3. Install Node.js and configure global npm writes

Inside WSL:

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

Any current Node LTS that satisfies the repo minimum also works. The important part is that `node` and `npm` resolve inside WSL and global npm installs do not require `sudo`.

## 4. Install `ds`, `codex`, and `uv`

Install the runtime package first:

```bash
npm install -g @researai/deepscientist
```

DeepScientist usually finds the bundled Codex dependency from that install. Verify it:

```bash
command -v codex
command -v ds
ds --version
```

If `codex` is still missing, repair it explicitly:

```bash
npm install -g @openai/codex
```

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version
```

## 5. Finish Codex setup before the first `ds`

Use one of the supported paths.

### 5.1 Default OpenAI login path

```bash
codex --login
```

If your local Codex build opens interactive setup through `codex` itself, use that entry instead.

### 5.2 Provider-backed profile path

If you already use a named profile such as `m27`, `glm`, `ark`, or `bailian`, verify it first:

```bash
codex --profile m27
```

Then keep the same profile for DeepScientist:

```bash
ds doctor --codex-profile m27
ds --codex-profile m27
```

Provider-specific details stay in [15 Codex Provider Setup](./15_CODEX_PROVIDER_SETUP.md).

## 6. Run diagnostics and start the runtime

Inside WSL:

```bash
ds doctor
```

If you use a provider-backed profile:

```bash
ds doctor --codex-profile m27
```

For a project-local home:

```bash
mkdir -p ~/projects/ds-demo
cd ~/projects/ds-demo
ds --here
```

For the default home:

```bash
ds
```

## 7. Browser access and launcher notes

Open the printed local URL from Chrome, Edge, or another Windows browser.

When you need to bind the daemon explicitly, use `--host`:

```bash
ds --host 0.0.0.0 --port 20999
```

Legacy scripts that still pass `--ip` keep working. The launcher prints a deprecation note and maps `--ip` to `--host`. Local browser access still uses `127.0.0.1` even when the bind host is `0.0.0.0`.

## 8. Common failure patterns

### WSL does not boot cleanly

- Run `wsl --status` and `wsl -l -v` in PowerShell.
- If you hit `HCS_E_CONNECTION_TIMEOUT` or Hyper-V startup errors, finish pending Windows updates and reboot before retrying.

### `codex` works in one shell but `ds doctor` fails

- Re-run the exact same profile inside the same WSL shell.
- If the working `codex` binary is outside `PATH`, pass it explicitly with `--codex /absolute/path/to/codex`.
- Re-check [15 Codex Provider Setup](./15_CODEX_PROVIDER_SETUP.md) for the profile-specific env vars and endpoint shape.

### `uv` runtime sync fails

The `uv` error text above the launcher guidance is the primary truth source. The common local causes are:

- an active Python environment such as `VIRTUAL_ENV`, `CONDA_PREFIX`, `PYTHONPATH`, or `PYTHONHOME`
- custom package index settings such as `PIP_*`, `UV_INDEX_URL`, or `UV_EXTRA_INDEX_URL`
- proxy or certificate overrides such as `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `SSL_CERT_FILE`, or `REQUESTS_CA_BUNDLE`

The fastest repair path is:

```bash
deactivate 2>/dev/null || true
conda deactivate 2>/dev/null || true
env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV -u CONDA_PREFIX ds doctor
```

Then rerun `ds`. Source checkouts may also need:

```bash
uv lock
```

### Port `20999` is busy

```bash
ds --status
ds --stop
```

Or launch on another port:

```bash
ds --port 21000
```

## 9. Related docs

- [00 Quick Start](./00_QUICK_START.md)
- [09 Doctor](./09_DOCTOR.md)
- [15 Codex Provider Setup](./15_CODEX_PROVIDER_SETUP.md)
- [Windows WSL2 setup skill](../../src/skills/windows-wsl2-setup/SKILL.md)
