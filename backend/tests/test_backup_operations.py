"""生产备份脚本与文档的安全契约测试。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import shlex
import subprocess

import pytest


WORKSPACE = Path(__file__).resolve().parents[2]
BACKUP_SCRIPT = WORKSPACE / 'scripts' / 'backup.sh'
VERIFY_SCRIPT = WORKSPACE / 'scripts' / 'verify_backup.sh'
BACKUP_GUIDE = WORKSPACE / 'docs' / 'BACKUP_GUIDE.md'
PRODUCTION_COMPOSE = WORKSPACE / 'deploy' / 'docker-compose.prod.yml'


@pytest.mark.parametrize('script_path', [BACKUP_SCRIPT, VERIFY_SCRIPT])
def test_backup_shell_script_has_valid_bash_syntax(script_path):
    bash = shutil.which('bash')
    if not bash:
        pytest.skip('bash is not installed')
    result = subprocess.run(
        [bash, '-n', script_path.relative_to(WORKSPACE).as_posix()],
        cwd=WORKSPACE,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors='replace')


def test_backup_script_publishes_complete_sets_only():
    script = BACKUP_SCRIPT.read_text(encoding='utf-8')

    assert 'pg_dump --format=custom' in script
    assert 'pg_restore --list' in script
    assert 'sha256sum --check' in script
    assert '.partial' in script
    assert 'flock -n' in script
    assert 'LOCAL_SET_COMPLETE' in script
    assert 'BACKUP_GPG_RECIPIENT' in script
    assert 'BACKUP_REMOTE_URI' in script
    assert 'BACKUP_ALERT_WEBHOOK' in script
    assert 'manifests/' in script
    assert 'db/' in script and 'media/' in script
    assert script.index('flock -n 9') < script.index('TIMESTAMP=')


def test_restore_drill_cannot_target_production_data():
    script = VERIFY_SCRIPT.read_text(encoding='utf-8')

    assert '--network none' in script
    assert '--single-transaction' in script
    assert 'sha256sum --check' in script
    assert 'media-restore' in script
    assert 'team_backup_drill_' in script
    assert 'DRILL_CONTAINER_ID=""' in script
    assert 'DRILL_CONTAINER_STARTED=false' in script
    assert 'if [[ "${DRILL_CONTAINER_STARTED}" == "true" ]]' in script
    assert 'docker rm -f "${DRILL_CONTAINER_ID}"' in script
    assert 'team_postgres_prod' not in script
    assert 'docker volume rm' not in script
    assert 'DROP DATABASE' not in script
    assert '/app/media' not in script


def test_backup_guide_matches_current_artifact_contract():
    guide = BACKUP_GUIDE.read_text(encoding='utf-8')

    assert 'pg_dump --format=custom' in guide
    assert 'backup_20260726T030000Z.sha256' in guide
    assert 'scripts/verify_backup.sh' in guide
    assert '--network none' in guide
    assert 'file:///mnt/offsite/team-management' in guide
    assert 'backup_failed' in guide
    assert 'backup_verification_failed' in guide
    assert '.sql.gz' not in guide
    assert 'docker volume rm' not in guide


def test_demo_backup_packages_use_a_persistent_production_volume():
    compose = PRODUCTION_COMPOSE.read_text(encoding='utf-8')

    assert 'demo_backup_data:/app/demo_backups' in compose
    assert '\n  demo_backup_data:' in compose


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8', newline='\n')
    path.chmod(0o755)


def _shell_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != 'nt':
        return str(resolved)
    drive = resolved.drive.rstrip(':').lower()
    tail = resolved.as_posix().split(':', 1)[1].lstrip('/')
    return f'/mnt/{drive}/{tail}'


def _shell_environment(fake_bin: Path) -> dict[str, str]:
    env = os.environ.copy()
    if os.name == 'nt':
        env['TEST_FAKE_BIN'] = _shell_path(fake_bin)
        env['WSLENV'] = ':'.join([
            'TEST_FAKE_BIN',
            'BACKUP_CONFIG_FILE',
            'BACKUP_DIR',
            'BACKUP_REMOTE_URI',
            'BACKUP_GPG_RECIPIENT',
            'BACKUP_ALERT_WEBHOOK',
            'FAKE_MEDIA_SOURCE',
            'FAKE_DOCKER_FAIL_DUMP',
            'FAKE_ALERT_FILE',
            'REAL_TAR',
            'RETAIN_DAYS',
        ])
    else:
        env['PATH'] = f'{fake_bin}{os.pathsep}{env["PATH"]}'
    return env


def _run_shell_script(
    bash: str,
    script: Path,
    arguments: list[str],
    env: dict[str, str],
) -> subprocess.CompletedProcess:
    arguments_with_script = [
        script.relative_to(WORKSPACE).as_posix(),
        *arguments,
    ]
    if os.name == 'nt':
        command = [
            bash,
            '-c',
            'export PATH="${TEST_FAKE_BIN}:/usr/local/sbin:/usr/local/bin:'
            '/usr/sbin:/usr/bin:/sbin:/bin"; exec '
            f'{shlex.join(arguments_with_script)}',
        ]
    else:
        command = [bash, *arguments_with_script]
    return subprocess.run(
        command,
        cwd=WORKSPACE,
        env=env,
        capture_output=True,
        check=False,
    )


def _output_text(value: bytes) -> str:
    return value.decode('utf-8', errors='replace')


def _fake_docker_script() -> str:
    return r"""#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  inspect)
    printf 'true\n'
    ;;
  run)
    printf 'fake-container-id\n'
    ;;
  rm)
    exit 0
    ;;
  exec)
    shift
    if [[ "${1:-}" == "-i" ]]; then
      shift
    fi
    container="${1:-}"
    shift
    command_name="${1:-}"
    shift || true
    case "${command_name}" in
      pg_dump)
        if [[ "${FAKE_DOCKER_FAIL_DUMP:-0}" == "1" ]]; then
          exit 9
        fi
        printf 'FAKE_POSTGRES_CUSTOM_DUMP\n'
        ;;
      pg_restore)
        cat >/dev/null
        ;;
      tar)
        "${REAL_TAR}" -czf - -C "${FAKE_MEDIA_SOURCE}" .
        ;;
      pg_isready)
        exit 0
        ;;
      psql)
        printf '3\n'
        ;;
      *)
        echo "unexpected fake docker command for ${container}: ${command_name}" >&2
        exit 91
        ;;
    esac
    ;;
  *)
    echo "unexpected fake docker invocation: $*" >&2
    exit 92
    ;;
esac
"""


def _fake_gpg_script() -> str:
    return r"""#!/usr/bin/env bash
set -euo pipefail
output=""
input=""
mode=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --list-keys)
      exit 0
      ;;
    --list-packets)
      test -s "$2"
      exit 0
      ;;
    --encrypt)
      mode="encrypt"
      shift
      ;;
    --decrypt)
      mode="decrypt"
      shift
      ;;
    --output)
      output="$2"
      shift 2
      ;;
    --recipient|--trust-model)
      shift 2
      ;;
    --batch|--yes)
      shift
      ;;
    *)
      input="$1"
      shift
      ;;
  esac
done
[[ "${mode}" == "encrypt" || "${mode}" == "decrypt" ]]
cp -- "${input}" "${output}"
"""


def test_backup_and_restore_drill_with_mocked_docker(tmp_path):
    bash = shutil.which('bash')
    real_tar = shutil.which('tar')
    if not bash or not real_tar:
        pytest.skip('bash and tar are required')

    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    _write_executable(fake_bin / 'docker', _fake_docker_script())
    _write_executable(fake_bin / 'gpg', _fake_gpg_script())

    media_source = tmp_path / 'media-source'
    media_source.mkdir()
    (media_source / 'receipt.txt').write_text('one-line receipt', encoding='utf-8')
    backup_root = tmp_path / 'backups'
    offsite_root = tmp_path / 'offsite'

    env = _shell_environment(fake_bin)
    env.update({
        'BACKUP_CONFIG_FILE': _shell_path(tmp_path / 'missing.env'),
        'BACKUP_DIR': _shell_path(backup_root),
        'BACKUP_REMOTE_URI': f'file://{_shell_path(offsite_root)}',
        'BACKUP_GPG_RECIPIENT': 'backup@example.test',
        'FAKE_MEDIA_SOURCE': _shell_path(media_source),
        'REAL_TAR': '/usr/bin/tar' if os.name == 'nt' else real_tar,
        'RETAIN_DAYS': '7',
    })

    backup_result = _run_shell_script(bash, BACKUP_SCRIPT, [], env)
    assert backup_result.returncode == 0, _output_text(backup_result.stderr)

    manifests = list((backup_root / 'manifests').glob('backup_*.sha256'))
    assert len(manifests) == 1
    manifest = manifests[0]
    timestamp = manifest.stem.removeprefix('backup_')
    db_file = backup_root / 'db' / f'db_{timestamp}.dump.gpg'
    media_file = backup_root / 'media' / f'media_{timestamp}.tar.gz.gpg'
    assert db_file.is_file()
    assert media_file.is_file()
    assert not list(backup_root.rglob('*.partial'))

    for artifact in (db_file, media_file):
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() in manifest.read_text(
            encoding='utf-8'
        )

    offsite_manifest = offsite_root / 'manifests' / manifest.name
    assert offsite_manifest.is_file()
    assert (offsite_root / 'db' / db_file.name).is_file()
    assert (offsite_root / 'media' / media_file.name).is_file()

    verify_result = _run_shell_script(
        bash,
        VERIFY_SCRIPT,
        [_shell_path(offsite_manifest)],
        env,
    )
    stdout = _output_text(verify_result.stdout)
    assert verify_result.returncode == 0, _output_text(verify_result.stderr)
    assert 'restore drill passed' in stdout
    assert 'table.users.rows=3' in stdout
    assert 'media.files=1' in stdout


def test_backup_failure_cleans_partials_and_sends_alert(tmp_path):
    bash = shutil.which('bash')
    real_tar = shutil.which('tar')
    if not bash or not real_tar:
        pytest.skip('bash and tar are required')

    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    _write_executable(fake_bin / 'docker', _fake_docker_script())
    alert_file = tmp_path / 'alert.json'
    _write_executable(
        fake_bin / 'curl',
        '#!/usr/bin/env bash\ncat > "${FAKE_ALERT_FILE}"\n',
    )

    media_source = tmp_path / 'media-source'
    media_source.mkdir()
    backup_root = tmp_path / 'backups'
    env = _shell_environment(fake_bin)
    env.update({
        'BACKUP_CONFIG_FILE': _shell_path(tmp_path / 'missing.env'),
        'BACKUP_DIR': _shell_path(backup_root),
        'BACKUP_ALERT_WEBHOOK': 'https://alerts.invalid/backup',
        'FAKE_ALERT_FILE': _shell_path(alert_file),
        'FAKE_DOCKER_FAIL_DUMP': '1',
        'FAKE_MEDIA_SOURCE': _shell_path(media_source),
        'REAL_TAR': '/usr/bin/tar' if os.name == 'nt' else real_tar,
    })

    result = _run_shell_script(bash, BACKUP_SCRIPT, [], env)

    assert result.returncode == 9
    assert alert_file.is_file()
    assert '"event":"backup_failed"' in alert_file.read_text(encoding='utf-8')
    assert not list(backup_root.rglob('*.partial'))
    assert not list((backup_root / 'manifests').glob('backup_*.sha256'))
