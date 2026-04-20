# Runner Contract

Status: `stable`  
Applies to: runner ids, provider-profile boundaries, connector prompt boundaries

## Stable runner ids

- `codex` is the stable default runner contract.
- `hermes_native_proof` is an opt-in proof lane for explicit full-agent-loop verification.
- `claude` and `opencode` are reserved experimental runner ids.

## Stable routing rules

- `config.default_runner` stays `codex` unless an operator deliberately changes it.
- `executor_kind = hermes_native_proof` is the only stable way to enter the Hermes proof lane.
- reserved experimental runner ids stay disabled by default and carry config/doc/test metadata only in the current release.

## Provider profile boundary

- MiniMax, GLM, Ark, Bailian, and similar provider-backed sessions stay on the Codex runner contract.
- provider profile metadata, `model: inherit`, env sanitization, and chat-wire MCP serialization stay inside the Codex compatibility path.

## Connector prompt boundary

- connector-specific transport and surface behavior belongs in connector prompt fragments and connector docs.
- runner/provider guidance stays outside connector prompt fragments.

