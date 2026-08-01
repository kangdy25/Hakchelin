#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  echo "Usage: $0 ENV_FILE BACKUP_DIRECTORY [DATABASE_URL_VARIABLE]" >&2
}

if (( $# < 2 || $# > 3 )); then
  usage
  exit 64
fi

env_file="$1"
backup_directory="$2"
database_url_variable="${3:-DATABASE_URL}"

if [[ ! -f "$env_file" ]]; then
  echo "Environment file does not exist: $env_file" >&2
  exit 66
fi

if [[ ! "$database_url_variable" =~ ^[A-Z][A-Z0-9_]*$ ]]; then
  echo "DATABASE_URL_VARIABLE must be an uppercase environment variable name." >&2
  exit 64
fi

mkdir -p "$backup_directory"
backup_directory="$(cd "$backup_directory" && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_name="hakchelin-neon-${timestamp}.dump"

umask 077

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file "$env_file" \
  --env "BACKUP_NAME=$backup_name" \
  --env "DATABASE_URL_VARIABLE=$database_url_variable" \
  --volume "$backup_directory:/backups" \
  postgres:18-alpine \
  sh -eu -c '
    database_url="$(printenv "$DATABASE_URL_VARIABLE")"
    if [ -z "$database_url" ]; then
      echo "$DATABASE_URL_VARIABLE is empty." >&2
      exit 78
    fi

    partial_dump="/backups/$BACKUP_NAME.partial"
    partial_manifest="/backups/$BACKUP_NAME.manifest.json.partial"
    cleanup() {
      rm -f "$partial_dump" "$partial_manifest"
    }
    trap cleanup EXIT INT TERM

    pg_dump \
      --dbname "$database_url" \
      --format custom \
      --compress 6 \
      --no-owner \
      --no-acl \
      --file "$partial_dump"

    pg_restore --list "$partial_dump" >/dev/null

    psql "$database_url" --no-psqlrc --tuples-only --no-align --command "
      SELECT jsonb_build_object(
        '\''accounts_user'\'', (SELECT count(*) FROM accounts_user),
        '\''meals_menu'\'', (SELECT count(*) FROM meals_menu),
        '\''reservations_reservation'\'', (SELECT count(*) FROM reservations_reservation),
        '\''wallet_pointtransaction'\'', (SELECT count(*) FROM wallet_pointtransaction),
        '\''payments_pointorder'\'', (SELECT count(*) FROM payments_pointorder),
        '\''chatbot_prompttemplate'\'', (SELECT count(*) FROM chatbot_prompttemplate),
        '\''chatbot_ailog'\'', (SELECT count(*) FROM chatbot_ailog),
        '\''chatbot_chatmessage'\'', (SELECT count(*) FROM chatbot_chatmessage)
      );
    " > "$partial_manifest"

    cd /backups
    mv "$partial_dump" "$BACKUP_NAME"
    mv "$partial_manifest" "$BACKUP_NAME.manifest.json"
    sha256sum "$BACKUP_NAME" > "$BACKUP_NAME.sha256"
    chmod 600 "$BACKUP_NAME" "$BACKUP_NAME.manifest.json" "$BACKUP_NAME.sha256"
    trap - EXIT INT TERM
  '

echo "Backup created: $backup_directory/$backup_name"
echo "Manifest created: $backup_directory/$backup_name.manifest.json"
echo "Checksum created: $backup_directory/$backup_name.sha256"
