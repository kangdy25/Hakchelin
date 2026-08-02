#!/usr/bin/env bash

set -Eeuo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

if [[ -d supabase ]]; then
  echo "Legacy BaaS directory must not exist after retirement: supabase/" >&2
  exit 1
fi

runtime_paths=(
  .github
  backend
  frontend
  infra
  packages
  package.json
  pnpm-lock.yaml
  pnpm-workspace.yaml
)

if rg --ignore-case \
  --glob '!backend/.env' \
  --glob '!**/__pycache__/**' \
  'supabase' "${runtime_paths[@]}"; then
  echo "Retired BaaS reference found in an application or deployment path." >&2
  exit 1
fi

echo "Runtime boundary check passed: Nuxt, Django, and Neon only."
