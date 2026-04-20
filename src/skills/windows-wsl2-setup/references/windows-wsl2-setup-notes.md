# Windows WSL2 Setup Notes

Use this note after the main skill triggers.

## Source-of-truth docs

- `README.md`
- `docs/en/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md`
- `docs/en/00_QUICK_START.md`
- `docs/en/15_CODEX_PROVIDER_SETUP.md`
- `docs/en/09_DOCTOR.md`

## Known-good end state

- A dedicated WSL2 Ubuntu distro exists and boots reliably.
- Linux-side `node`, `npm`, `git`, `uv`, `codex`, and `ds` all resolve inside the distro.
- `codex exec --skip-git-repo-check "Print exactly OK and exit."` succeeds.
- `ds doctor` shows a healthy Codex probe.
- `ds` starts inside WSL.
- Windows can open `http://127.0.0.1:20999`.

## Practical install sequence

### 1. Pre-flight WSL health

Run in PowerShell:

```powershell
wsl -l -v
wsl --status
wsl -d Ubuntu -- echo hello
```

If `echo hello` fails with `HCS_E_CONNECTION_TIMEOUT`:

```powershell
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' `
  -Name PendingFileRenameOperations -ErrorAction SilentlyContinue
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime
wsl --shutdown
```

If the distro still fails to boot, ask for a reboot before continuing.

Check free memory when startup looks unstable:

```powershell
$mem = Get-CimInstance Win32_OperatingSystem
[math]::Round($mem.FreePhysicalMemory / 1MB, 2)
```

### 2. Create or select a dedicated distro

Prefer a dedicated Ubuntu WSL2 distro for this runtime.
Ubuntu 22.04 or 24.04 is a practical default.

Example:

```powershell
wsl --install Ubuntu-24.04
```

After first boot, create a normal Linux user and keep work under that account.

### 3. Disable Windows PATH injection

Inside WSL:

```bash
printf '[interop]\nappendWindowsPath=false\n' | sudo tee /etc/wsl.conf
```

Then back in PowerShell:

```powershell
wsl --terminate <distro>
```

Re-enter WSL and verify `command -v node` or `command -v codex` no longer resolves to `/mnt/c/...`.

### 4. Install Linux prerequisites

Use the current repo docs as the version floor.
A practical Ubuntu baseline is:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git sudo build-essential python3-venv python3-pip
```

If the distro still uses the 22.04 package split:

```bash
sudo apt-get install -y python3.10-venv
```

Install a current Node LTS that satisfies the repo minimum:

```bash
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
printf 'deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main\n' | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt-get update
sudo apt-get install -y nodejs
```

Set a user-local npm prefix:

```bash
mkdir -p "$HOME/.npm-global" "$HOME/.local/bin"
npm config set prefix "$HOME/.npm-global"
echo 'export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"' >> ~/.bashrc
echo 'export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"' >> ~/.profile
```

Install `uv`, Codex CLI, and the runtime:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
npm install -g @openai/codex
npm install -g @researai/deepscientist
```

Provider-backed compatibility lanes may need `@openai/codex@0.57.0`.
Use the provider setup guide as the version truth for that lane.

### 5. Auth paths

Pick one working path and verify it before `ds doctor`.

#### A. Interactive OpenAI login

Inside WSL:

```bash
codex
```

or:

```bash
codex --login
```

#### B. Provider-backed profile

Follow `docs/en/15_CODEX_PROVIDER_SETUP.md`.
Validate the profile directly in the WSL terminal before using `ds --codex-profile <name>`.

#### C. Direct API key

Write `~/.codex/auth.json`:

```json
{
  "OPENAI_API_KEY": "sk-..."
}
```

#### D. OpenAI-compatible relay

Write `~/.codex/config.toml` with the relay `base_url`, provider name, and model settings required by that relay.
Write the key to `~/.codex/auth.json`.

Practical guardrails:

- keep `model_reasoning_effort` within the CLI-supported enum for the installed Codex version
- older Codex CLIs such as `0.57.0` accept `minimal`, `low`, `medium`, and `high`
- verify the relay path with `codex exec` before opening `ds`

#### E. Reuse Windows auth

When Windows already has a working `C:\Users\<user>\.codex\auth.json`:

```bash
mkdir -p ~/.codex
[ -f ~/.codex/auth.json ] && cp ~/.codex/auth.json ~/.codex/auth.json.bak.$(date +%Y%m%d-%H%M%S)
cp /mnt/c/Users/<user>/.codex/auth.json ~/.codex/auth.json
chmod 600 ~/.codex/auth.json
```

This path is useful when browser auth inside WSL is awkward.

## Proxy and NAT repair

Check direct connectivity from WSL first:

```bash
curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://chatgpt.com/
curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://github.com/
```

If the target needs a Windows-side proxy, inspect listeners in PowerShell:

```powershell
pwsh -File scripts/find-wsl-proxy.ps1
```

If the user already gave a likely port:

```powershell
pwsh -File scripts/find-wsl-proxy.ps1 -Ports 7890
```

Then inside WSL:

```bash
host_ip="$(ip route 2>/dev/null | awk '/^default/ { print $3; exit }')"
curl -s --max-time 8 -x "http://$host_ip:<port>" -o /dev/null -w '%{http_code}' https://github.com/
```

Persist proxy env only after a confirmed port:

```bash
cat > "$HOME/.wsl-proxy-env" <<'EOF'
host_ip="$(ip route 2>/dev/null | awk '/^default/ { print $3; exit }')"
proxy_port="<confirmed-port>"
if [ -n "$host_ip" ]; then
    export http_proxy="http://$host_ip:$proxy_port"
    export https_proxy="http://$host_ip:$proxy_port"
    export HTTP_PROXY="$http_proxy"
    export HTTPS_PROXY="$https_proxy"
    export ALL_PROXY="$http_proxy"
fi
EOF
echo '[ -f "$HOME/.wsl-proxy-env" ] && source "$HOME/.wsl-proxy-env"' >> ~/.bashrc
echo '[ -f "$HOME/.wsl-proxy-env" ] && source "$HOME/.wsl-proxy-env"' >> ~/.profile
```

## Validation chain

Run in order:

```bash
whoami
command -v node npm git uv codex ds
cd /tmp
codex exec --skip-git-repo-check "Print exactly OK and exit."
ds doctor
ds
```

Then open in the Windows browser:

```text
http://127.0.0.1:20999
```

## Common failure patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| `HCS_E_CONNECTION_TIMEOUT` | Pending reboot or stale Hyper-V state | Reboot Windows after `wsl --shutdown` |
| `command -v ds` or `codex` returns `/mnt/c/...` | Windows PATH injection is still active | Fix `/etc/wsl.conf`, terminate the distro, re-enter, verify again |
| `python3.10-venv` package is missing | Ubuntu release changed the package name | Use `python3-venv` on newer Ubuntu |
| `model is not supported` or auth succeeds then calls fail | Subscription or relay config mismatch | Verify the chosen auth lane with `codex exec` |
| `unknown variant xhigh` | Older Codex CLI enum set | Use a supported reasoning value such as `high` |
| Proxy test returns `000` | WSL cannot reach the Windows proxy | Enable LAN access and re-test with the gateway IP |
| `ds` exits when the launching shell closes | The process lifetime is bound to that shell | Relaunch in a persistent terminal or supervised process |
| The first `ds doctor` takes a long time | `uv` is still downloading or preparing the Python runtime | Wait for the bootstrap to finish |

## Windows to WSL command transport

Shell quoting gets brittle when Windows shells call `wsl.exe ... bash -c "..."` with many `$` variables.
Two reliable patterns are:

1. write a `.sh` file and run it from WSL
2. wrap the WSL command in a small `.ps1` file and execute that script from PowerShell

An interactive WSL terminal is the cleanest path for Linux-side admin work.
