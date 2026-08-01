#!/usr/bin/env bash

set -Eeuo pipefail

repository_directory="${REPOSITORY_DIRECTORY:-/opt/hakchelin}"
compose_env_file="${COMPOSE_ENV_FILE:-/etc/hakchelin/compose.env}"
deployment_env_file="${DEPLOYMENT_ENV_FILE:-/var/lib/hakchelin/api-image.env}"
failed_commit_file="${FAILED_COMMIT_FILE:-/var/lib/hakchelin/last-failed-commit}"
compose_file="${COMPOSE_FILE:-infra/lightsail/docker-compose.yml}"
health_url="${PUBLIC_HEALTH_URL:-https://api.hakchelin.cloud/healthz}"
image_repository="${API_IMAGE_REPOSITORY:-ghcr.io/kangdy25/hakchelin-api}"
lock_file="${DEPLOY_LOCK_FILE:-/run/lock/hakchelin-deploy.lock}"

for required_command in curl docker flock git; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    echo "Required command is missing: $required_command" >&2
    exit 69
  fi
done

write_private_file() {
  local destination="$1"
  local content="$2"
  local temporary_file

  mkdir -p "$(dirname "$destination")"
  temporary_file="${destination}.tmp.$$"
  umask 077
  printf '%s\n' "$content" > "$temporary_file"
  chmod 600 "$temporary_file"
  mv "$temporary_file" "$destination"
}

mkdir -p "$(dirname "$lock_file")"
exec 9>"$lock_file"
if ! flock --nonblock 9; then
  echo "Another deployment is already running; skipping."
  exit 0
fi

if [[ ! -d "$repository_directory/.git" ]]; then
  echo "Git repository does not exist: $repository_directory" >&2
  exit 1
fi

if [[ ! -f "$compose_env_file" ]]; then
  echo "Compose environment file does not exist: $compose_env_file" >&2
  exit 1
fi

cd "$repository_directory"

if [[ "$(git symbolic-ref --short HEAD)" != "main" ]]; then
  echo "Deployment repository must be on main." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Deployment repository has local changes; refusing to overwrite them." >&2
  exit 1
fi

git fetch --quiet origin main
target_commit="$(git rev-parse origin/main)"
target_image="${image_repository}:sha-${target_commit}"

if [[ -f "$failed_commit_file" && "$(tr -d '\r\n' < "$failed_commit_file")" == "$target_commit" ]]; then
  echo "Commit $target_commit already failed deployment; waiting for a newer main commit." >&2
  exit 1
fi

api_container_id="$(docker compose --env-file "$compose_env_file" -f "$compose_file" ps --quiet api 2>/dev/null || true)"
previous_image=""
if [[ -n "$api_container_id" ]]; then
  previous_image="$(docker inspect --format '{{.Config.Image}}' "$api_container_id")"
fi

current_commit="$(git rev-parse HEAD)"
current_image=""
if [[ -f "$deployment_env_file" ]]; then
  current_image="$(sed -n 's/^API_IMAGE=//p' "$deployment_env_file")"
fi

if [[ "$current_commit" == "$target_commit" && "$current_image" == "$target_image" ]]; then
  echo "Commit $target_commit is already deployed."
  exit 0
fi

# The immutable SHA tag exists only after the main CI tests and image publication succeed.
docker pull "$target_image"
git merge --ff-only "$target_commit"

write_private_file "$deployment_env_file" "API_IMAGE=$target_image"
compose=(docker compose --env-file "$compose_env_file" --env-file "$deployment_env_file" -f "$compose_file")

rollback_image() {
  if [[ -z "$previous_image" ]]; then
    echo "No previous API image is available for automatic rollback." >&2
    return 1
  fi

  echo "Rolling back containers to $previous_image" >&2
  write_private_file "$deployment_env_file" "API_IMAGE=$previous_image"
  "${compose[@]}" up --detach --no-build --force-recreate
}

if ! "${compose[@]}" up --detach --no-build --force-recreate; then
  write_private_file "$failed_commit_file" "$target_commit"
  rollback_image || true
  exit 1
fi

health_ok=false
for _ in $(seq 1 18); do
  health_response="$(curl --fail --silent --show-error --max-time 10 "$health_url" 2>/dev/null || true)"
  if [[ "$health_response" == *'"status": "ok"'* ]]; then
    health_ok=true
    break
  fi
  sleep 5
done

if [[ "$health_ok" != "true" ]]; then
  echo "Deployment health check failed for $target_commit." >&2
  write_private_file "$failed_commit_file" "$target_commit"
  rollback_image || true
  exit 1
fi

rm -f "$failed_commit_file"
echo "Deployed $target_commit using $target_image"
