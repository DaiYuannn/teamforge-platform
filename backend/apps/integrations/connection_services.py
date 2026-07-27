import ipaddress
import os
import socket
import subprocess
from urllib.parse import urljoin, urlparse

import requests


class IntegrationConnectionError(Exception):
    pass


def _validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise IntegrationConnectionError('Only HTTP and HTTPS remote URLs are supported')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise IntegrationConnectionError('Remote host cannot be resolved') from exc
    for address in addresses:
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise IntegrationConnectionError('Private or local network addresses are not allowed')


def _response_metadata(response):
    content_type = response.headers.get('content-type', '')
    result = {'status_code': response.status_code, 'content_type': content_type[:120]}
    if 'json' in content_type:
        try:
            payload = response.json()
            result['payload'] = payload if isinstance(payload, (dict, list)) else str(payload)[:2000]
        except ValueError:
            result['body_preview'] = response.text[:2000]
    else:
        result['body_preview'] = response.text[:2000]
    return result


def connect_external_platform(platform, *, sync=False):
    config = platform.config or {}
    path = config.get('sync_path', '') if sync else config.get('health_path', '')
    url = urljoin(platform.api_url.rstrip('/') + '/', str(path).lstrip('/'))
    _validate_public_url(url)
    api_key = platform.get_api_key()
    headers = {'Accept': 'application/json'}
    if api_key:
        header = str(config.get('auth_header', 'Authorization'))
        scheme = str(config.get('auth_scheme', 'Bearer')).strip()
        headers[header] = f'{scheme} {api_key}'.strip()
    method = str(config.get('sync_method' if sync else 'health_method', 'GET')).upper()
    if method not in ('GET', 'POST'):
        raise IntegrationConnectionError('Connection method must be GET or POST')
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=config.get('sync_payload') if method == 'POST' else None,
            timeout=(3, 10),
        )
        response.raise_for_status()
        return _response_metadata(response)
    except requests.RequestException as exc:
        message = str(exc).replace(api_key, '***') if api_key else str(exc)
        raise IntegrationConnectionError(message[:1000]) from exc


def connect_git_repository(repository):
    _validate_public_url(repository.url)
    token = repository.get_token()
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    if token:
        env.update({
            'GIT_CONFIG_COUNT': '1',
            'GIT_CONFIG_KEY_0': 'http.extraHeader',
            'GIT_CONFIG_VALUE_0': f'Authorization: Bearer {token}',
        })
    ref = f'refs/heads/{repository.branch}'
    try:
        result = subprocess.run(
            ['git', 'ls-remote', '--heads', repository.url, ref],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IntegrationConnectionError('Git connection timed out or Git is unavailable') from exc
    if result.returncode != 0:
        error = (result.stderr or result.stdout or 'Git connection failed').strip()
        if token:
            error = error.replace(token, '***')
        raise IntegrationConnectionError(error[:1000])
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise IntegrationConnectionError(f'Remote branch {repository.branch} was not found')
    commit = lines[0].split()[0]
    if len(commit) < 7:
        raise IntegrationConnectionError('Remote repository returned an invalid commit')
    return {'branch': repository.branch, 'commit': commit}
