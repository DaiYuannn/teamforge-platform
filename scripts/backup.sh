#!/usr/bin/env bash
# Production PostgreSQL + protected media backup.
# Configure with environment variables or /etc/team-management/backup.env.

set -Eeuo pipefail
umask 077

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/team-management/backup.env}"
if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${CONFIG_FILE}"
fi

BACKUP_DIR="${BACKUP_DIR:-/opt/backups/team-management}"
RETAIN_DAYS="${RETAIN_DAYS:-30}"
PG_CONTAINER="${PG_CONTAINER:-team_postgres_prod}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-team_backend_prod}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-team_management}"
BACKUP_REMOTE_URI="${BACKUP_REMOTE_URI:-}"
BACKUP_ALERT_WEBHOOK="${BACKUP_ALERT_WEBHOOK:-}"
BACKUP_GPG_RECIPIENT="${BACKUP_GPG_RECIPIENT:-}"

if [[ "${BACKUP_DIR}" != /* || "${BACKUP_DIR}" == "/" ]]; then
  echo "BACKUP_DIR must be an absolute non-root directory" >&2
  exit 2
fi
if [[ ! "${RETAIN_DAYS}" =~ ^[0-9]+$ ]] || (( RETAIN_DAYS < 1 )); then
  echo "RETAIN_DAYS must be a positive integer" >&2
  exit 2
fi

mkdir -p -- "${BACKUP_DIR}"
BACKUP_DIR="$(cd "${BACKUP_DIR}" && pwd -P)"
DB_DIR="${BACKUP_DIR}/db"
MEDIA_DIR="${BACKUP_DIR}/media"
MANIFEST_DIR="${BACKUP_DIR}/manifests"
mkdir -p -- "${DB_DIR}" "${MEDIA_DIR}" "${MANIFEST_DIR}"

# Acquire the process lock before choosing names. Otherwise, two jobs starting
# in the same second could share a timestamp and the losing job's error cleanup
# could remove the active job's partial files.
if ! command -v flock >/dev/null 2>&1; then
  echo "required command not found: flock" >&2
  exit 127
fi
exec 9>"${BACKUP_DIR}/.backup.lock"
if ! flock -n 9; then
  echo "another backup process already holds ${BACKUP_DIR}/.backup.lock" >&2
  exit 75
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_TMP="${DB_DIR}/db_${TIMESTAMP}.dump.partial"
MEDIA_TMP="${MEDIA_DIR}/media_${TIMESTAMP}.tar.gz.partial"
DB_ENCRYPTED_TMP="${DB_DIR}/db_${TIMESTAMP}.dump.gpg.partial"
MEDIA_ENCRYPTED_TMP="${MEDIA_DIR}/media_${TIMESTAMP}.tar.gz.gpg.partial"
MANIFEST_TMP="${MANIFEST_DIR}/backup_${TIMESTAMP}.sha256.partial"
DB_FINAL="${DB_DIR}/db_${TIMESTAMP}.dump"
MEDIA_FINAL="${MEDIA_DIR}/media_${TIMESTAMP}.tar.gz"
MANIFEST="${MANIFEST_DIR}/backup_${TIMESTAMP}.sha256"
LOCAL_SET_COMPLETE=false

now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

send_failure_alert() {
  local exit_code="$1"
  if [[ -n "${BACKUP_ALERT_WEBHOOK}" ]] && command -v curl >/dev/null 2>&1; then
    printf '{"event":"backup_failed","host":"%s","timestamp":"%s","exit_code":%s}\n' \
      "$(hostname)" "${TIMESTAMP}" "${exit_code}" |
      curl --fail --silent --show-error --max-time 10 \
        -H 'Content-Type: application/json' \
        --data-binary @- "${BACKUP_ALERT_WEBHOOK}" >/dev/null || true
  fi
}

on_error() {
  local exit_code=$?
  trap - ERR
  rm -f -- \
    "${DB_TMP}" "${MEDIA_TMP}" \
    "${DB_ENCRYPTED_TMP}" "${MEDIA_ENCRYPTED_TMP}" \
    "${MANIFEST_TMP}"
  if [[ "${LOCAL_SET_COMPLETE}" != "true" ]]; then
    rm -f -- \
      "${DB_DIR}/db_${TIMESTAMP}.dump" \
      "${DB_DIR}/db_${TIMESTAMP}.dump.gpg" \
      "${MEDIA_DIR}/media_${TIMESTAMP}.tar.gz" \
      "${MEDIA_DIR}/media_${TIMESTAMP}.tar.gz.gpg" \
      "${MANIFEST_DIR}/backup_${TIMESTAMP}.sha256"
  fi
  send_failure_alert "${exit_code}"
  echo "[$(now)] backup failed with exit code ${exit_code}" >&2
  exit "${exit_code}"
}
trap on_error ERR

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command not found: $1" >&2
    return 127
  }
}

for command_name in docker tar sha256sum find hostname; do
  require_command "${command_name}"
done
if [[ -n "${BACKUP_ALERT_WEBHOOK}" ]]; then
  require_command curl
fi
if [[ -n "${BACKUP_GPG_RECIPIENT}" ]]; then
  require_command gpg
  gpg --batch --list-keys "${BACKUP_GPG_RECIPIENT}" >/dev/null
fi

REMOTE_KIND=""
REMOTE_LOCAL_DIR=""
if [[ -n "${BACKUP_REMOTE_URI}" ]]; then
  case "${BACKUP_REMOTE_URI}" in
    file://*)
      REMOTE_KIND="local"
      REMOTE_LOCAL_DIR="${BACKUP_REMOTE_URI#file://}"
      ;;
    /*)
      REMOTE_KIND="local"
      REMOTE_LOCAL_DIR="${BACKUP_REMOTE_URI}"
      ;;
    s3://*)
      REMOTE_KIND="s3"
      require_command aws
      ;;
    *)
      REMOTE_KIND="rclone"
      require_command rclone
      ;;
  esac
  if [[ "${REMOTE_KIND}" == "local" ]]; then
    if [[ "${REMOTE_LOCAL_DIR}" != /* || "${REMOTE_LOCAL_DIR}" == "/" ]]; then
      echo "file backup destination must be an absolute non-root directory" >&2
      false
    fi
    mkdir -p -- "${REMOTE_LOCAL_DIR}"
    REMOTE_LOCAL_DIR="$(cd "${REMOTE_LOCAL_DIR}" && pwd -P)"
    if [[ "${REMOTE_LOCAL_DIR}" == "${BACKUP_DIR}" ||
          "${REMOTE_LOCAL_DIR}" == "${BACKUP_DIR}/"* ||
          "${BACKUP_DIR}" == "${REMOTE_LOCAL_DIR}/"* ]]; then
      echo "local and remote backup directories must not contain each other" >&2
      false
    fi
  fi
fi

[[ "$(docker inspect -f '{{.State.Running}}' "${PG_CONTAINER}")" == "true" ]]
[[ "$(docker inspect -f '{{.State.Running}}' "${BACKEND_CONTAINER}")" == "true" ]]

echo "[$(now)] creating PostgreSQL custom-format backup"
docker exec "${PG_CONTAINER}" \
  pg_dump --format=custom --no-owner --no-acl -U "${DB_USER}" "${DB_NAME}" \
  > "${DB_TMP}"
test -s "${DB_TMP}"
docker exec -i "${PG_CONTAINER}" pg_restore --list < "${DB_TMP}" >/dev/null

echo "[$(now)] creating protected media backup"
docker exec "${BACKEND_CONTAINER}" \
  tar --exclude='*.tmp' --exclude='*.partial' -czf - -C /app/media . \
  > "${MEDIA_TMP}"
test -s "${MEDIA_TMP}"
tar -tzf "${MEDIA_TMP}" >/dev/null

if [[ -n "${BACKUP_GPG_RECIPIENT}" ]]; then
  echo "[$(now)] encrypting backup artifacts"
  gpg --batch --yes --trust-model always \
    --encrypt --recipient "${BACKUP_GPG_RECIPIENT}" \
    --output "${DB_ENCRYPTED_TMP}" "${DB_TMP}"
  gpg --batch --yes --trust-model always \
    --encrypt --recipient "${BACKUP_GPG_RECIPIENT}" \
    --output "${MEDIA_ENCRYPTED_TMP}" "${MEDIA_TMP}"
  test -s "${DB_ENCRYPTED_TMP}"
  test -s "${MEDIA_ENCRYPTED_TMP}"
  gpg --batch --list-packets "${DB_ENCRYPTED_TMP}" >/dev/null
  gpg --batch --list-packets "${MEDIA_ENCRYPTED_TMP}" >/dev/null
  rm -f -- "${DB_TMP}" "${MEDIA_TMP}"
  DB_FINAL="${DB_DIR}/db_${TIMESTAMP}.dump.gpg"
  MEDIA_FINAL="${MEDIA_DIR}/media_${TIMESTAMP}.tar.gz.gpg"
  mv -- "${DB_ENCRYPTED_TMP}" "${DB_FINAL}"
  mv -- "${MEDIA_ENCRYPTED_TMP}" "${MEDIA_FINAL}"
else
  mv -- "${DB_TMP}" "${DB_FINAL}"
  mv -- "${MEDIA_TMP}" "${MEDIA_FINAL}"
fi

(
  cd "${BACKUP_DIR}"
  sha256sum "db/$(basename "${DB_FINAL}")" "media/$(basename "${MEDIA_FINAL}")"
) > "${MANIFEST_TMP}"
mv -- "${MANIFEST_TMP}" "${MANIFEST}"
(
  cd "${BACKUP_DIR}"
  sha256sum --check "manifests/$(basename "${MANIFEST}")"
)
LOCAL_SET_COMPLETE=true

copy_to_local_remote() {
  local source_path="$1"
  local relative_path="$2"
  local destination="${REMOTE_LOCAL_DIR}/${relative_path}"
  mkdir -p -- "$(dirname "${destination}")"
  cp -- "${source_path}" "${destination}.partial"
  chmod 600 "${destination}.partial"
  mv -- "${destination}.partial" "${destination}"
}

copy_remote_artifacts() {
  local db_relative="db/$(basename "${DB_FINAL}")"
  local media_relative="media/$(basename "${MEDIA_FINAL}")"
  local manifest_relative="manifests/$(basename "${MANIFEST}")"

  echo "[$(now)] copying backup set to remote storage"
  case "${REMOTE_KIND}" in
    local)
      copy_to_local_remote "${DB_FINAL}" "${db_relative}"
      copy_to_local_remote "${MEDIA_FINAL}" "${media_relative}"
      # The manifest is the completion marker and is deliberately copied last.
      copy_to_local_remote "${MANIFEST}" "${manifest_relative}"
      (
        cd "${REMOTE_LOCAL_DIR}"
        sha256sum --check "${manifest_relative}"
      )
      ;;
    s3)
      aws s3 cp "${DB_FINAL}" "${BACKUP_REMOTE_URI%/}/${db_relative}"
      aws s3 cp "${MEDIA_FINAL}" "${BACKUP_REMOTE_URI%/}/${media_relative}"
      aws s3 cp "${MANIFEST}" "${BACKUP_REMOTE_URI%/}/${manifest_relative}"
      ;;
    rclone)
      rclone copyto "${DB_FINAL}" "${BACKUP_REMOTE_URI%/}/${db_relative}"
      rclone copyto "${MEDIA_FINAL}" "${BACKUP_REMOTE_URI%/}/${media_relative}"
      rclone copyto "${MANIFEST}" "${BACKUP_REMOTE_URI%/}/${manifest_relative}"
      ;;
  esac
}

if [[ -n "${REMOTE_KIND}" ]]; then
  copy_remote_artifacts
fi

echo "[$(now)] pruning local backups older than ${RETAIN_DAYS} days"
find "${DB_DIR}" -type f \( -name 'db_*.dump' -o -name 'db_*.dump.gpg' \) \
  -mtime "+${RETAIN_DAYS}" -delete
find "${MEDIA_DIR}" -type f \( -name 'media_*.tar.gz' -o -name 'media_*.tar.gz.gpg' \) \
  -mtime "+${RETAIN_DAYS}" -delete
find "${MANIFEST_DIR}" -type f -name 'backup_*.sha256' \
  -mtime "+${RETAIN_DAYS}" -delete
find "${BACKUP_DIR}" -type f -name '*.partial' -mtime +1 -delete

trap - ERR
echo "[$(now)] backup complete"
echo "database=${DB_FINAL}"
echo "media=${MEDIA_FINAL}"
echo "manifest=${MANIFEST}"
