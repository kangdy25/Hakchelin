#!/usr/bin/env bash

set -uo pipefail

compose_env_file="${COMPOSE_ENV_FILE:-/etc/hakchelin/compose.env}"
compose_file="${COMPOSE_FILE:-/opt/hakchelin/infra/lightsail/docker-compose.yml}"
public_health_url="${PUBLIC_HEALTH_URL:-https://api.hakchelin.cloud/healthz}"
disk_usage_limit="${DISK_USAGE_LIMIT_PERCENT:-85}"
memory_available_limit="${MEMORY_AVAILABLE_LIMIT_PERCENT:-10}"

failures=()

if [[ ! -f "$compose_env_file" ]]; then
  echo "Compose environment file is missing: $compose_env_file" >&2
  exit 1
fi

if [[ ! -f "$compose_file" ]]; then
  echo "Compose file is missing: $compose_file" >&2
  exit 1
fi

compose=(docker compose --env-file "$compose_env_file" -f "$compose_file")

for service in caddy api worker beat redis; do
  container_id="$("${compose[@]}" ps --quiet "$service" 2>/dev/null)"
  if [[ -z "$container_id" ]]; then
    failures+=("$service container is missing")
    continue
  fi

  container_status="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null)"
  if [[ "$container_status" != "running" ]]; then
    failures+=("$service is $container_status")
  fi
done

for service in api redis; do
  container_id="$("${compose[@]}" ps --quiet "$service" 2>/dev/null)"
  if [[ -n "$container_id" ]]; then
    health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_id" 2>/dev/null)"
    if [[ "$health_status" != "healthy" ]]; then
      failures+=("$service health is $health_status")
    fi
  fi
done

migrate_container_id="$("${compose[@]}" ps --all --quiet migrate 2>/dev/null)"
if [[ -z "$migrate_container_id" ]]; then
  failures+=("migrate container is missing")
else
  migrate_exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$migrate_container_id" 2>/dev/null)"
  if [[ "$migrate_exit_code" != "0" ]]; then
    failures+=("migrate exited with $migrate_exit_code")
  fi
fi

if ! "${compose[@]}" exec --no-TTY worker celery -A config inspect ping --timeout=5 >/dev/null 2>&1; then
  failures+=("Celery worker ping failed")
fi

health_response="$(curl --fail --silent --show-error --max-time 10 "$public_health_url" 2>/dev/null)"
if [[ "$health_response" != *'"status": "ok"'* ]]; then
  failures+=("public health endpoint failed")
fi

disk_usage="$(df -P / | awk 'NR == 2 { gsub(/%/, "", $5); print $5 }')"
if [[ "$disk_usage" =~ ^[0-9]+$ ]] && (( disk_usage >= disk_usage_limit )); then
  failures+=("root disk usage is ${disk_usage}%")
fi

if [[ -r /proc/meminfo ]]; then
  memory_total="$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo)"
  memory_available="$(awk '/^MemAvailable:/ { print $2 }' /proc/meminfo)"
  if [[ "$memory_total" =~ ^[0-9]+$ && "$memory_available" =~ ^[0-9]+$ && memory_total -gt 0 ]]; then
    memory_available_percent=$(( memory_available * 100 / memory_total ))
    if (( memory_available_percent <= memory_available_limit )); then
      failures+=("available memory is ${memory_available_percent}%")
    fi
  fi
fi

if (( ${#failures[@]} > 0 )); then
  printf 'Hakchelin health check failed:\n' >&2
  printf -- '- %s\n' "${failures[@]}" >&2
  exit 1
fi

echo "Hakchelin health check passed: containers, migration, Celery, HTTPS, disk, memory"
