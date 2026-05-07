#!/usr/bin/env bash
set -euo pipefail

lane="${1:-smoke}"

case "$lane" in
  smoke|fast)
    uv run pytest \
      tests/test_runtime_contract_surface.py \
      tests/test_api_contract_surface.py \
      tests/test_skill_contracts.py
    ;;
  contracts)
    uv run python scripts/audit_repo_hygiene.py
    uv run pytest \
      tests/test_runtime_contract_surface.py \
      tests/test_api_contract_surface.py \
      tests/test_skill_contracts.py \
      tests/test_startup_contract_ownership.py \
      tests/test_repo_hygiene_audit.py
    ;;
  full)
    uv run pytest
    ;;
  release)
    uv run pytest
    npm run build:release
    npm pack --dry-run
    ;;
  *)
    echo "Unknown lane: $lane" >&2
    echo "Usage: scripts/verify.sh [smoke|fast|contracts|full|release]" >&2
    exit 1
    ;;
esac
