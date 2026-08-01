#!/usr/bin/env bash

set -Eeuo pipefail

canonical_url="${CANONICAL_URL:-https://hakchelin.cloud/}"
redirect_url="${REDIRECT_URL:-https://www.hakchelin.cloud/}"

curl --fail --silent --show-error --location --max-time 15 \
  --retry 2 --retry-all-errors \
  --output /dev/null \
  "$canonical_url"

read -r status redirect_target < <(
  curl --silent --show-error --max-time 15 \
    --output /dev/null \
    --write-out '%{http_code} %{redirect_url}\n' \
    "$redirect_url"
)

if [[ "$status" != "308" ]]; then
  echo "Expected HTTP 308 from $redirect_url, received $status." >&2
  exit 1
fi

if [[ "$redirect_target" != "$canonical_url" ]]; then
  echo "Expected redirect target $canonical_url, received $redirect_target." >&2
  exit 1
fi

echo "Domain routing passed: $redirect_url -> $canonical_url (308)"
