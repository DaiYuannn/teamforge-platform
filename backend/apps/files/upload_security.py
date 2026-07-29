"""Shared filename and size checks for direct and archive material uploads."""

from pathlib import Path, PurePosixPath

from rest_framework import serializers


MAX_DIRECT_MATERIAL_BYTES = 25 * 1024 * 1024
DANGEROUS_MATERIAL_EXTENSIONS = {
    '.app', '.apk', '.bat', '.cmd', '.com', '.cpl', '.dll', '.dmg', '.exe',
    '.hta', '.jar', '.js', '.jse', '.lnk', '.msi', '.msp', '.pif', '.ps1',
    '.reg', '.scr', '.sh', '.vb', '.vbe', '.vbs', '.wsf', '.wsh',
}


def normalized_archive_path(value: str) -> str:
    """Return a safe normalized POSIX path or raise a serializer error."""
    raw = str(value or '').replace('\\', '/')
    if not raw or '\x00' in raw:
        raise serializers.ValidationError('资料路径为空或包含非法字符')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts:
        raise serializers.ValidationError(f'资料路径不安全: {value}')
    normalized = str(path)
    if normalized in {'', '.'}:
        raise serializers.ValidationError(f'资料路径不安全: {value}')
    return normalized


def validate_material_filename(name: str) -> str:
    normalized = normalized_archive_path(name)
    suffix = Path(normalized).suffix.casefold()
    if suffix in DANGEROUS_MATERIAL_EXTENSIONS:
        raise serializers.ValidationError(f'不允许上传可执行或脚本文件: {name}')
    return normalized


def validate_uploaded_material(uploaded_file, *, max_bytes=MAX_DIRECT_MATERIAL_BYTES):
    validate_material_filename(getattr(uploaded_file, 'name', ''))
    size = int(getattr(uploaded_file, 'size', 0) or 0)
    if size <= 0:
        raise serializers.ValidationError('上传文件不能为空')
    if size > max_bytes:
        raise serializers.ValidationError(
            f'单个资料不能超过 {max_bytes // (1024 * 1024)} MB'
        )
    return uploaded_file
