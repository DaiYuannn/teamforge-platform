#!/usr/bin/env bash
# Non-destructive restore drill. Verifies one complete backup set, extracts its
# media into a temporary directory, and restores the database into an isolated
# temporary PostgreSQL container. It never connects to the production database.

set -Eeuo pipefail
umask 077

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /absolute/path/to/manifests/backup_YYYYMMDDTHHMMSSZ.sha256" >&2
  echo "       $0 /absolute/path/to/db/db_YYYYMMDDTHHMMSSZ.dump[.gpg]" >&2
  exit 2
fi

INPUT_PATH="$1"
if [[ "${INPUT_PATH}" != /* || ! -f "${INPUT_PATH}" ]]; then
  echo "backup input must be an existing absolute file: ${INPUT_PATH}" >&2
  exit 2
fi

VERIFY_ALERT_WEBHOOK="${VERIFY_ALERT_WEBHOOK:-${BACKUP_ALERT_WEBHOOK:-}}"
RESTORE_DRILL_POSTGRES_IMAGE="${RESTORE_DRILL_POSTGRES_IMAGE:-postgres:16-alpine}"
RESTORE_DRILL_TIMEOUT="${RESTORE_DRILL_TIMEOUT:-60}"
VERIFY_TABLES="${VERIFY_TABLES:-django_migrations users projects tasks file_assets operation_logs}"
read -r -a VERIFY_TABLE_ARRAY <<< "${VERIFY_TABLES}"
if [[ "${#VERIFY_TABLE_ARRAY[@]}" -eq 0 ]]; then
  echo "VERIFY_TABLES must contain at least one table" >&2
  exit 2
fi

if [[ ! "${RESTORE_DRILL_TIMEOUT}" =~ ^[0-9]+$ ]] || (( RESTORE_DRILL_TIMEOUT < 1 )); then
  echo "RESTORE_DRILL_TIMEOUT must be a positive integer" >&2
  exit 2
fi

INPUT_PATH="$(cd "$(dirname "${INPUT_PATH}")" && pwd -P)/$(basename "${INPUT_PATH}")"
INPUT_NAME="$(basename "${INPUT_PATH}")"

if [[ "${INPUT_NAME}" =~ ^backup_([0-9]{8}T[0-9]{6}Z)\.sha256$ ]]; then
  TIMESTAMP="${BASH_REMATCH[1]}"
  MANIFEST="${INPUT_PATH}"
  BACKUP_ROOT="$(cd "$(dirname "${MANIFEST}")/.." && pwd -P)"
elif [[ "${INPUT_NAME}" =~ ^db_([0-9]{8}T[0-9]{6}Z)\.dump(\.gpg)?$ ]]; then
  TIMESTAMP="${BASH_REMATCH[1]}"
  BACKUP_ROOT="$(cd "$(dirname "${INPUT_PATH}")/.." && pwd -P)"
  MANIFEST="${BACKUP_ROOT}/manifests/backup_${TIMESTAMP}.sha256"
else
  echo "unsupported backup filename: ${INPUT_NAME}" >&2
  exit 2
fi

if [[ ! -f "${MANIFEST}" ]]; then
  echo "manifest not found: ${MANIFEST}" >&2
  exit 2
fi

TEMP_BASE="${TMPDIR:-/tmp}"
if [[ "${TEMP_BASE}" != /* || ! -d "${TEMP_BASE}" ]]; then
  echo "TMPDIR must be an existing absolute directory" >&2
  exit 2
fi
TEMP_BASE="$(cd "${TEMP_BASE}" && pwd -P)"
TEMP_DIR="$(mktemp -d "${TEMP_BASE%/}/team-backup-verify.XXXXXX")"
DRILL_CONTAINER="team_backup_drill_$$_$(date -u +%H%M%S)"
DRILL_CONTAINER_ID=""
DRILL_CONTAINER_STARTED=false
DRILL_DB="restore_drill"
DRILL_PASSWORD=""
DB_RESTORE_FILE=""
MEDIA_RESTORE_FILE=""

now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

send_failure_alert() {
  local exit_code="$1"
  if [[ -n "${VERIFY_ALERT_WEBHOOK}" ]] && command -v curl >/dev/null 2>&1; then
    printf '{"event":"backup_verification_failed","host":"%s","timestamp":"%s","exit_code":%s}\n' \
      "$(hostname)" "${TIMESTAMP}" "${exit_code}" |
      curl --fail --silent --show-error --max-time 10 \
        -H 'Content-Type: application/json' \
        --data-binary @- "${VERIFY_ALERT_WEBHOOK}" >/dev/null || true
  fi
}

cleanup() {
  if [[ "${DRILL_CONTAINER_STARTED}" == "true" ]]; then
    docker rm -f "${DRILL_CONTAINER_ID}" >/dev/null 2>&1 || true
  fi
  case "${TEMP_DIR}" in
    "${TEMP_BASE%/}"/team-backup-verify.*)
      rm -rf -- "${TEMP_DIR}"
      ;;
    *)
      echo "refusing to remove unexpected temporary path: ${TEMP_DIR}" >&2
      ;;
  esac
}

on_exit() {
  local exit_code=$?
  trap - EXIT
  cleanup
  if (( exit_code != 0 )); then
    send_failure_alert "${exit_code}"
    echo "[$(now)] backup verification failed with exit code ${exit_code}" >&2
  fi
  exit "${exit_code}"
}
trap on_exit EXIT

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command not found: $1" >&2
    return 127
  }
}

for command_name in docker tar sha256sum openssl hostname find grep wc tr mktemp; do
  require_command "${command_name}"
done
if [[ -n "${VERIFY_ALERT_WEBHOOK}" ]]; then
  require_command curl
fi

mapfile -t MANIFEST_LINES < "${MANIFEST}"
if [[ "${#MANIFEST_LINES[@]}" -ne 2 ]]; then
  echo "manifest must contain exactly two checksum entries" >&2
  false
fi

DB_RELATIVE=""
MEDIA_RELATIVE=""
for manifest_line in "${MANIFEST_LINES[@]}"; do
  if [[ ! "${manifest_line}" =~ ^[0-9a-fA-F]{64}[[:space:]][[:space:]]([^[:space:]]+)$ ]]; then
    echo "invalid manifest entry: ${manifest_line}" >&2
    false
  fi
  relative_path="${BASH_REMATCH[1]}"
  case "${relative_path}" in
    "db/db_${TIMESTAMP}.dump"|"db/db_${TIMESTAMP}.dump.gpg")
      [[ -z "${DB_RELATIVE}" ]]
      DB_RELATIVE="${relative_path}"
      ;;
    "media/media_${TIMESTAMP}.tar.gz"|"media/media_${TIMESTAMP}.tar.gz.gpg")
      [[ -z "${MEDIA_RELATIVE}" ]]
      MEDIA_RELATIVE="${relative_path}"
      ;;
    *)
      echo "manifest entry does not belong to backup ${TIMESTAMP}: ${relative_path}" >&2
      false
      ;;
  esac
done

if [[ -z "${DB_RELATIVE}" || -z "${MEDIA_RELATIVE}" ]]; then
  echo "manifest must reference one database dump and one media archive" >&2
  false
fi
if [[ "${DB_RELATIVE}" == *.gpg && "${MEDIA_RELATIVE}" != *.gpg ]] ||
   [[ "${DB_RELATIVE}" != *.gpg && "${MEDIA_RELATIVE}" == *.gpg ]]; then
  echo "database and media artifacts must use the same encryption mode" >&2
  false
fi

DB_PATH="${BACKUP_ROOT}/${DB_RELATIVE}"
MEDIA_PATH="${BACKUP_ROOT}/${MEDIA_RELATIVE}"
if [[ ! -f "${DB_PATH}" || ! -f "${MEDIA_PATH}" ]]; then
  echo "manifest references a missing artifact" >&2
  false
fi

echo "[$(now)] verifying SHA-256 manifest"
(
  cd "${BACKUP_ROOT}"
  sha256sum --check "manifests/$(basename "${MANIFEST}")"
)

if [[ "${DB_PATH}" == *.gpg ]]; then
  require_command gpg
  DB_RESTORE_FILE="${TEMP_DIR}/restore.dump"
  MEDIA_RESTORE_FILE="${TEMP_DIR}/media.tar.gz"
  gpg --batch --decrypt --output "${DB_RESTORE_FILE}" "${DB_PATH}"
  gpg --batch --decrypt --output "${MEDIA_RESTORE_FILE}" "${MEDIA_PATH}"
else
  DB_RESTORE_FILE="${DB_PATH}"
  MEDIA_RESTORE_FILE="${MEDIA_PATH}"
fi

test -s "${DB_RESTORE_FILE}"
test -s "${MEDIA_RESTORE_FILE}"

echo "[$(now)] validating and extracting media into an isolated temporary directory"
if tar -tzf "${MEDIA_RESTORE_FILE}" |
   grep -E '(^/|(^|/)\.\.(/|$))' >/dev/null; then
  echo "media archive contains an unsafe path" >&2
  false
fi
mkdir -p -- "${TEMP_DIR}/media-restore"
tar -xzf "${MEDIA_RESTORE_FILE}" \
  --no-same-owner --no-same-permissions \
  -C "${TEMP_DIR}/media-restore"
MEDIA_FILE_COUNT="$(
  find "${TEMP_DIR}/media-restore" -type f -print | wc -l | tr -d '[:space:]'
)"

for table_name in "${VERIFY_TABLE_ARRAY[@]}"; do
  if [[ ! "${table_name}" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "invalid table name in VERIFY_TABLES: ${table_name}" >&2
    false
  fi
done

DRILL_PASSWORD="$(openssl rand -hex 24)"
echo "[$(now)] starting isolated PostgreSQL restore container"
DRILL_CONTAINER_ID="$(
  docker run -d --rm \
    --name "${DRILL_CONTAINER}" \
    --label team-management.backup-drill=true \
    --network none \
    -e POSTGRES_PASSWORD="${DRILL_PASSWORD}" \
    -e POSTGRES_DB="${DRILL_DB}" \
    "${RESTORE_DRILL_POSTGRES_IMAGE}"
)"
test -n "${DRILL_CONTAINER_ID}"
DRILL_CONTAINER_STARTED=true

ready=false
for (( attempt = 0; attempt < RESTORE_DRILL_TIMEOUT; attempt++ )); do
  if docker exec "${DRILL_CONTAINER_ID}" \
    pg_isready -U postgres -d "${DRILL_DB}" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "${ready}" != "true" ]]; then
  echo "restore drill database did not become ready in time" >&2
  false
fi

docker exec -i "${DRILL_CONTAINER_ID}" pg_restore --list \
  < "${DB_RESTORE_FILE}" >/dev/null
docker exec -i "${DRILL_CONTAINER_ID}" \
  pg_restore --exit-on-error --single-transaction --no-owner --no-acl \
  -U postgres -d "${DRILL_DB}" < "${DB_RESTORE_FILE}"

echo "[$(now)] validating restored core tables"
for table_name in "${VERIFY_TABLE_ARRAY[@]}"; do
  row_count="$(
    docker exec "${DRILL_CONTAINER_ID}" \
      psql -U postgres -d "${DRILL_DB}" -v ON_ERROR_STOP=1 -Atc \
      "SELECT COUNT(*) FROM public.\"${table_name}\";"
  )"
  if [[ ! "${row_count}" =~ ^[0-9]+$ ]]; then
    echo "invalid row count for ${table_name}: ${row_count}" >&2
    false
  fi
  echo "table.${table_name}.rows=${row_count}"
done

echo "media.files=${MEDIA_FILE_COUNT}"
echo "restore drill passed: ${MANIFEST}"
