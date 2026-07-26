"""受保护媒体文件的存储与响应工具。"""

from __future__ import annotations

import mimetypes
import re
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlencode

from django.conf import settings
from django.core import signing
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404, HttpResponse
from django.utils.http import content_disposition_header


MEDIA_SIGNING_SALT = 'team-management.protected-media.v1'
SAFE_INLINE_MEDIA_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/avif',
    'application/pdf',
}


def normalize_media_name(name: str) -> str:
    """
    返回安全的媒体相对路径。

    FileField 在数据库中保存 POSIX 风格相对路径。拒绝绝对路径、父目录跳转
    和空路径，防止签名端或响应端被路径穿越利用。
    """
    raw_name = str(name or '').replace('\\', '/')
    if (
        not raw_name
        or raw_name.startswith('/')
        or re.match(r'^[a-zA-Z]:/', raw_name)
        or '\x00' in raw_name
    ):
        raise ValueError('invalid media path')
    normalized = raw_name
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or '..' in path.parts:
        raise ValueError('invalid media path')
    return path.as_posix()


def is_public_media(name: str) -> bool:
    """只有显式放入 public/ 目录的资产可以由 Nginx 公开直出。"""
    try:
        normalized = normalize_media_name(name)
    except ValueError:
        return False
    return normalized == 'public' or normalized.startswith('public/')


def create_protected_media_token(name: str) -> str:
    """为经过业务 API 授权后返回的媒体地址生成限时能力令牌。"""
    normalized = normalize_media_name(name)
    return signing.dumps(
        {'path': normalized, 'version': 1},
        salt=MEDIA_SIGNING_SALT,
        compress=True,
    )


def load_protected_media_token(token: str) -> str:
    """校验媒体令牌及有效期，并返回安全的媒体相对路径。"""
    max_age = int(getattr(settings, 'PROTECTED_MEDIA_URL_TTL', 7200))
    payload = signing.loads(token, salt=MEDIA_SIGNING_SALT, max_age=max_age)
    if not isinstance(payload, dict) or payload.get('version') != 1:
        raise signing.BadSignature('invalid media token payload')
    return normalize_media_name(payload.get('path', ''))


class ProtectedMediaStorage(FileSystemStorage):
    """
    默认媒体存储。

    public/ 下的资产使用普通公开 URL；其他文件返回带签名和有效期的 API
    地址。数据库中的 FileField 值保持不变，不需要数据迁移。
    """

    def url(self, name):
        normalized = normalize_media_name(name)
        if is_public_media(normalized):
            return super().url(normalized)

        endpoint = getattr(
            settings,
            'PROTECTED_MEDIA_API_URL',
            '/api/v1/common/media/',
        )
        token = create_protected_media_token(normalized)
        separator = '&' if '?' in endpoint else '?'
        return f'{endpoint}{separator}{urlencode({"token": token})}'


def _resolve_media_file(name: str) -> tuple[str, Path]:
    normalized = normalize_media_name(name)
    media_root = Path(settings.MEDIA_ROOT).resolve()
    target = (media_root / Path(*PurePosixPath(normalized).parts)).resolve()
    if target == media_root or media_root not in target.parents:
        raise Http404('媒体文件不存在')
    if not target.is_file():
        raise Http404('媒体文件不存在')
    return normalized, target


def protected_media_response(
    name: str,
    *,
    as_attachment: bool = False,
    download_name: str | None = None,
):
    """
    返回受保护媒体。

    生产环境由 Nginx 的 internal location 发送文件，开发/测试环境回退为
    Django FileResponse。调用方必须在调用前完成业务权限或签名校验。
    """
    normalized, target = _resolve_media_file(name)
    filename = download_name or target.name
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    # HTML、SVG 等主动内容即使有合法签名，也不应以内联同源文档执行。
    as_attachment = as_attachment or content_type not in SAFE_INLINE_MEDIA_TYPES

    if getattr(settings, 'PROTECTED_MEDIA_USE_X_ACCEL_REDIRECT', False):
        internal_prefix = getattr(
            settings,
            'PROTECTED_MEDIA_INTERNAL_PREFIX',
            '/_protected_media/',
        )
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = (
            f'{internal_prefix.rstrip("/")}/{quote(normalized, safe="/")}'
        )
        response['Content-Length'] = target.stat().st_size
        response['Content-Disposition'] = content_disposition_header(
            as_attachment, filename
        )
    else:
        response = FileResponse(
            target.open('rb'),
            as_attachment=as_attachment,
            filename=filename,
            content_type=content_type,
        )

    response['Cache-Control'] = 'private, no-store'
    response['Pragma'] = 'no-cache'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Frame-Options'] = 'DENY'
    return response


class StorageBackend(ABC):
    """文件存储统一接口，保留供对象存储扩展使用。"""

    @abstractmethod
    def save(self, name, content, max_length=None):
        raise NotImplementedError

    @abstractmethod
    def delete(self, name):
        raise NotImplementedError

    @abstractmethod
    def exists(self, name):
        raise NotImplementedError

    @abstractmethod
    def url(self, name):
        raise NotImplementedError

    @abstractmethod
    def size(self, name):
        raise NotImplementedError

    @abstractmethod
    def listdir(self, path):
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """
    原有存储抽象的兼容适配器。

    URL 生成同样使用 ProtectedMediaStorage，防止旧调用方重新暴露永久
    /media/ 地址。
    """

    def __init__(self, location=None, base_url=None):
        self._storage = ProtectedMediaStorage(
            location=location,
            base_url=base_url,
        )

    def save(self, name, content, max_length=None):
        return self._storage.save(name, content, max_length=max_length)

    def delete(self, name):
        self._storage.delete(name)

    def exists(self, name):
        return self._storage.exists(name)

    def url(self, name):
        return self._storage.url(name)

    def size(self, name):
        return self._storage.size(name)

    def listdir(self, path):
        return self._storage.listdir(path)

    def path(self, name):
        return self._storage.path(name)


_storage_backend = None


def get_storage_backend():
    """获取全局本地存储适配器。"""
    global _storage_backend
    if _storage_backend is None:
        _storage_backend = LocalStorageBackend(
            location=getattr(settings, 'MEDIA_ROOT', None),
            base_url=getattr(settings, 'MEDIA_URL', None),
        )
    return _storage_backend
