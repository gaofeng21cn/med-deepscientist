---
name: windows-wsl2-setup
description: Install, repair, and validate the current `ds` runtime on Windows with WSL2 until Linux-side `codex exec`, `ds doctor`, and the Windows browser can reach the local Web UI. Use when an agent needs to bootstrap or fix a Windows plus WSL2 DeepScientist environment, including WSL pre-flight checks, Linux-side Node or uv or Codex CLI setup, auth or relay configuration, proxy or NAT repair, and common failure recovery.
---

# Windows WSL2 Setup

Use this skill for workstation setup and repair on a Windows machine that runs the `ds` runtime inside WSL2.

This skill is an environment-maintenance surface.
Keep research-stage work on the stage skills such as `scout`, `baseline`, and `experiment`.

## One-liner for humans

Copy this to an AI coding agent when you want it to do the install:

> Set up DeepScientist on this Windows machine through WSL2 by following `src/skills/windows-wsl2-setup/SKILL.md` in the current repo. Keep going until Linux-side `codex exec --skip-git-repo-check "Print exactly OK and exit."` works, `ds doctor` passes, and the Windows browser can open `http://127.0.0.1:20999`.

## Truth sources

Use these in order before changing anything:

1. `README.md`
2. `docs/en/22_WINDOWS_WSL2_DEPLOYMENT_GUIDE.md`
3. `docs/en/00_QUICK_START.md`
4. `docs/en/15_CODEX_PROVIDER_SETUP.md`
5. `docs/en/09_DOCTOR.md`
6. [`references/windows-wsl2-setup-notes.md`](references/windows-wsl2-setup-notes.md)

Treat the repo docs as the command truth.
Treat the deployment guide as the stable Windows install, validation, and startup path.
Treat the reference note as Windows-specific operating guidance, auth options, proxy or NAT repair flow, and failure triage.

## End state

Keep working until all checks below pass:

1. WSL2 can start the target distro reliably.
2. Linux-side `node`, `npm`, `git`, `uv`, `codex`, and `ds` resolve to Linux paths.
3. `codex exec --skip-git-repo-check "Print exactly OK and exit."` succeeds inside WSL.
4. `ds doctor` reports a healthy Codex path.
5. `ds` starts inside WSL and the Windows browser can open `http://127.0.0.1:20999`.

## Human actions

Some steps need the human at the keyboard. Stop and ask at these gates:

| Gate | Human action |
|---|---|
| `HCS_E_CONNECTION_TIMEOUT` or WSL will not boot | Reboot Windows and finish pending updates |
| Proxy only listens on `127.0.0.1` | Enable LAN access in the Windows proxy app |
| Browser-based Codex login is required | Complete `codex` login in an interactive terminal |
| Firewall blocks WSL or Hyper-V networking | Allow the relevant Windows networking surface |

## Workflow

### 1. Inspect first

Check the real machine state before installing:

- `wsl -l -v`
- `wsl --status`
- run the target distro with a trivial command such as `wsl -d <distro> -- echo hello`
- inside WSL, check `command -v node npm git uv codex ds`

If an existing distro is healthy, reuse it only when it is already dedicated to this workflow or the user explicitly wants that distro.
Prefer a dedicated Ubuntu WSL2 distro for a clean setup lane.

### 2. Run pre-flight gates

Before installing packages, verify:

- WSL can actually boot
- available memory is reasonable for WSL startup
- the machine does not have a pending reboot that blocks Hyper-V startup

Use the reference note for the exact PowerShell checks.
If WSL fails to start cleanly, repair that first.

### 3. Keep Linux binaries Linux-side

Inside the target distro:

- install the baseline packages needed by the current repo docs
- install a current Node LTS that satisfies the repo minimum
- install `uv`
- install `@openai/codex` or the provider-compatible version required by the chosen auth path
- install `@researai/deepscientist`

Disable Windows PATH injection in the WSL distro before trusting binary resolution.
After changing `/etc/wsl.conf`, terminate and re-enter the distro, then re-check `command -v`.

### 4. Configure Codex auth

Choose the lightest working auth path:

1. normal OpenAI login inside an interactive terminal
2. provider-backed Codex profile that already works in the terminal
3. direct API key
4. OpenAI-compatible relay configuration
5. Windows-side auth file reuse when GUI login inside WSL is awkward

The repo's provider setup guide remains authoritative for provider profiles.
The reference note contains the relay and auth-file reuse patterns.

### 5. Repair proxy or NAT only when needed

Test direct connectivity from WSL first.
If the machine already reaches `chatgpt.com` and `github.com`, keep the network shape simple.

When a Windows-side proxy is involved:

- inspect the Windows listener shape with `scripts/find-wsl-proxy.ps1`
- prefer the WSL default gateway IP from `ip route`
- test the candidate proxy from WSL before persisting environment variables
- persist proxy env only after one port is confirmed

### 6. Validate in order

Run validation in this order:

1. `whoami`
2. `command -v node npm git uv codex ds`
3. `codex exec --skip-git-repo-check "Print exactly OK and exit."`
4. `ds doctor`
5. `ds`
6. open `http://127.0.0.1:20999` from the Windows browser

Use `docs/en/09_DOCTOR.md` for runtime repair if `ds doctor` exposes a downstream issue.

## When to open the reference note

Open [`references/windows-wsl2-setup-notes.md`](references/windows-wsl2-setup-notes.md) when you need:

- PowerShell pre-flight commands
- WSL distro setup details
- Linux package install examples
- auth decision support
- proxy or NAT troubleshooting
- common failure patterns
- Windows to WSL shell escaping workarounds

## Bundled helper

Use [`scripts/find-wsl-proxy.ps1`](scripts/find-wsl-proxy.ps1) from Windows PowerShell to inspect candidate proxy listeners that WSL might need to reach.
