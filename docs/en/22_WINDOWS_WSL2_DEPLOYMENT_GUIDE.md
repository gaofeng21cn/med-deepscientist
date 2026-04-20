# 22 Windows WSL2 Deployment Guide

This guide is the stable Windows operator path for the current MedDeepScientist fork. The recommended shape is simple: run `ds` inside WSL2, keep the runtime toolchain on the Linux side, verify Codex before the first launch, then open the local UI from the Windows browser.

## Truth sources

Use these repo docs in this order when you need to confirm behavior:

1. `README.md`
2. [00 Quick Start](./00_QUICK_START.md)
3. [15 Codex Provider Setup](./15_CODEX_PROVIDER_SETUP.md)
4. [09 Doctor](./09_DOCTOR.md)
5. [`src/skills/windows-wsl2-setup/SKILL.md`](../../src/skills/windows-wsl2-setup/SKILL.md)

This guide turns those repo truths into one Windows-specific workflow. The docs above remain authoritative when command details move.

## What success looks like

Treat the setup as complete only when all checks below pass in order:

1. `wsl -l -v`, `wsl --status`, and `wsl -d <distro> -- echo hello` succeed from Windows.
2. Inside WSL, `command -v node npm git uv codex ds` all resolve to Linux paths.
3. `codex exec --skip-git-repo-check "Print exactly OK and exit."` succeeds inside WSL.
4. `ds doctor` reports a healthy Codex path.
5. `ds` starts inside WSL and the Windows browser opens `http://127.0.0.1:20999`.

## 1. Prepare Windows and WSL2 first

Use a dedicated Ubuntu WSL2 distro when you want the cleanest lane.

Run in Windows PowerShell:

```powershell
wsl -l -v
wsl --status
wsl -d Ubuntu -- echo hello
```

If the distro does not boot cleanly, fix that first. `HCS_E_CONNECTION_TIMEOUT`, pending Windows updates, or Hyper-V startup issues belong at the Windows layer.

## 2. Keep runtime binaries on the Linux side

Inside WSL, disable Windows PATH injection before you trust binary resolution:

```bash
printf '[interop]\nappendWindowsPath=false\n' | sudo tee /etc/wsl.conf
```

Then terminate and re-enter the distro from PowerShell:

```powershell
wsl --terminate Ubuntu
```

Back in WSL, install baseline packages, a current Node LTS, and user-local npm prefixes:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git sudo build-essential python3-venv python3-pip

mkdir -p "$HOME/.npm-global" "$HOME/.local/bin"
npm config set prefix "$HOME/.npm-global"
printf '\nexport PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
printf '\nexport PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"\n' >> "$HOME/.profile"
source "$HOME/.bashrc"
```

Install the runtime toolchain in WSL:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
npm install -g @openai/codex
npm install -g @researai/deepscientist
```

If your environment already depends on a provider-compatible Codex version or wrapper, keep that version choice in [15 Codex Provider Setup](./15_CODEX_PROVIDER_SETUP.md). This guide stays version-agnostic on purpose.

## 3. Configure Codex before `ds`

Pick one working Codex path and verify it in WSL before you open `ds`:

### Default login path

```bash
codex --login
```

If your CLI does not expose `--login`, run `codex` and finish the interactive login there.

### Provider-backed profile path

```bash
codex --profile <profile-name>
```

Later, start DeepScientist with the same profile:

```bash
ds --codex-profile <profile-name>
```

The current fork keeps model and reasoning selection inherited from your local Codex defaults unless you explicitly override them. `--codex-profile` selects a profile for one launch. `--codex` selects a specific Codex executable for one launch.

## 4. Validate in order

Run these checks inside WSL:

```bash
whoami
command -v node npm git uv codex ds
codex exec --skip-git-repo-check "Print exactly OK and exit."
ds doctor
```

If you use a provider-backed profile, include it in the doctor step:

```bash
ds doctor --codex-profile <profile-name>
```

Only continue after `codex exec` and `ds doctor` are both healthy.

## 5. Start the runtime and open it from Windows

Start from a working directory inside WSL:

```bash
mkdir -p ~/deepscientist-work
cd ~/deepscientist-work
ds --here
```

If you use a provider-backed profile:

```bash
ds --here --codex-profile <profile-name>
```

The stable local browser address is:

```text
http://127.0.0.1:20999
```

`--host 0.0.0.0` is valid when you want the daemon to bind on all interfaces. The local browser entry still stays on `127.0.0.1`. `--ip` remains a deprecated launcher alias; `--host` is the current flag.

## 6. Proxy and networking notes

Test direct connectivity from WSL before you persist proxy variables:

```bash
curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://chatgpt.com/
curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://github.com/
```

When you really need a Windows-side proxy, inspect candidate listeners from PowerShell:

```powershell
pwsh -File scripts/find-wsl-proxy.ps1
```

Then test the WSL gateway route before you export proxy variables permanently.

## 7. Common repair paths

| Symptom | What to check |
|---|---|
| `command -v codex` or `ds` points into `/mnt/c/...` | Re-check `/etc/wsl.conf`, terminate the distro, then verify again |
| `codex exec` fails | Fix login, profile, or provider config before opening `ds` |
| `ds doctor` fails during uv bootstrap or sync | Read the original uv error first, then check `VIRTUAL_ENV`, `CONDA_PREFIX`, `PYTHONPATH`, `PYTHONHOME`, `PIP_*`, `UV_INDEX_URL`, `UV_EXTRA_INDEX_URL`, `HTTP(S)_PROXY`, `SSL_CERT_FILE`, and `REQUESTS_CA_BUNDLE` |
| uv sync fails from a source checkout after Python dependency changes | Run `uv lock`, then retry |
| uv sync fails from the npm package install | Focus on local Python, proxy, certificate, or package-index configuration; the npm package already includes the locked `uv.lock` |
| Windows browser cannot reach `127.0.0.1:20999` | Keep `ds` running inside WSL, then check firewall, proxy, and WSL networking state |

## Related docs

- [00 Quick Start](./00_QUICK_START.md)
- [09 Doctor](./09_DOCTOR.md)
- [15 Codex Provider Setup](./15_CODEX_PROVIDER_SETUP.md)
- [`src/skills/windows-wsl2-setup/SKILL.md`](../../src/skills/windows-wsl2-setup/SKILL.md)
