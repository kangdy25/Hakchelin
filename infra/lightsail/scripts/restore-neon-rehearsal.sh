#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  echo "Usage: $0 BACKUP_FILE" >&2
}

if (( $# != 1 )); then
  usage
  exit 64
fi

backup_file="$1"
manifest_file="${backup_file}.manifest.json"
checksum_file="${backup_file}.sha256"

for required_file in "$backup_file" "$manifest_file" "$checksum_file"; do
  if [[ ! -f "$required_file" ]]; then
    echo "Required rehearsal file does not exist: $required_file" >&2
    exit 66
  fi
done

backup_directory="$(cd "$(dirname "$backup_file")" && pwd)"
backup_name="$(basename "$backup_file")"
container_name="hakchelin-restore-$RANDOM-$$"

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker run --detach \
  --name "$container_name" \
  --env POSTGRES_DB=hakchelin_restore \
  --env POSTGRES_PASSWORD=rehearsal-only \
  --health-cmd="pg_isready -U postgres -d hakchelin_restore" \
  --health-interval=1s \
  --health-timeout=3s \
  --health-retries=30 \
  postgres:18-alpine >/dev/null

for _ in $(seq 1 30); do
  if [[ "$(docker inspect --format '{{.State.Health.Status}}' "$container_name")" == "healthy" ]]; then
    break
  fi
  sleep 1
done

if [[ "$(docker inspect --format '{{.State.Health.Status}}' "$container_name")" != "healthy" ]]; then
  echo "Rehearsal PostgreSQL did not become healthy." >&2
  exit 1
fi

docker run --rm \
  --volume "$backup_directory:/backups:ro" \
  postgres:18-alpine \
  sh -eu -c "cd /backups && sha256sum -c '$backup_name.sha256'"

docker cp "$backup_file" "$container_name:/tmp/hakchelin.dump"
docker exec "$container_name" pg_restore \
  --username postgres \
  --dbname hakchelin_restore \
  --exit-on-error \
  --no-owner \
  --no-acl \
  /tmp/hakchelin.dump

count_query="
  SELECT jsonb_build_object(
    'accounts_user', (SELECT count(*) FROM accounts_user),
    'meals_menu', (SELECT count(*) FROM meals_menu),
    'reservations_reservation', (SELECT count(*) FROM reservations_reservation),
    'wallet_pointtransaction', (SELECT count(*) FROM wallet_pointtransaction),
    'payments_pointorder', (SELECT count(*) FROM payments_pointorder),
    'chatbot_prompttemplate', (SELECT count(*) FROM chatbot_prompttemplate),
    'chatbot_ailog', (SELECT count(*) FROM chatbot_ailog),
    'chatbot_chatmessage', (SELECT count(*) FROM chatbot_chatmessage)
  );
"

expected_counts="$(tr -d '\r\n' < "$manifest_file")"
restored_counts="$(docker exec "$container_name" psql \
  --username postgres \
  --dbname hakchelin_restore \
  --no-psqlrc \
  --tuples-only \
  --no-align \
  --command "$count_query")"

if [[ "$restored_counts" != "$expected_counts" ]]; then
  echo "Restored table counts do not match the backup manifest." >&2
  echo "Expected: $expected_counts" >&2
  echo "Restored: $restored_counts" >&2
  exit 1
fi

docker exec "$container_name" psql \
  --username postgres \
  --dbname hakchelin_restore \
  --no-psqlrc \
  --set ON_ERROR_STOP=1 \
  --command "
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM django_migrations) THEN
        RAISE EXCEPTION 'django_migrations is empty';
      END IF;
      IF EXISTS (SELECT 1 FROM accounts_user WHERE current_point < 0) THEN
        RAISE EXCEPTION 'negative current_point found';
      END IF;
    END
    \$\$;
  " >/dev/null

echo "Restore rehearsal succeeded."
echo "Restored counts: $restored_counts"
