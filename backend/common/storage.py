"""
存储后端抽象
支持后续扩展为对象存储（OSS/S3/MinIO等）
"""
import os
from abc import ABC, abstractmethod
from django.core.files.storage import FileSystemStorage


class StorageBackend(ABC):
    """
    存储后端抽象基类
    定义文件存储的统一接口，子类实现具体存储逻辑
    """

    @abstractmethod
    def save(self, name, content, max_length=None):
        """保存文件"""
        pass

    @abstractmethod
    def delete(self, name):
        """删除文件"""
        pass

    @abstractmethod
    def exists(self, name):
        """检查文件是否存在"""
        pass

    @abstractmethod
    def url(self, name):
        """获取文件访问URL"""
        pass

    @abstractmethod
    def size(self, name):
        """获取文件大小"""
        pass

    @abstractmethod
    def listdir(self, path):
        """列出目录内容"""
        pass


class LocalStorageBackend(StorageBackend):
    """
    本地文件存储后端
    基于 Django FileSystemStorage 实现
    """

    def __init__(self, location=None, base_url=None):
        """
        :param location: 存储根目录
        :param base_url: 访问基础URL
        """
        self._storage = FileSystemStorage(
            location=location,
            base_url=base_url,
        )

    def save(self, name, content, max_length=None):
        """保存文件到本地文件系统"""
        return self._storage.save(name, content, max_length=max_length)

    def delete(self, name):
        """从本地文件系统删除文件"""
        self._storage.delete(name)

    def exists(self, name):
        """检查本地文件是否存在"""
        return self._storage.exists(name)

    def url(self, name):
        """获取本地文件的访问URL"""
        return self._storage.url(name)

    def size(self, name):
        """获取本地文件大小"""
        return self._storage.size(name)

    def listdir(self, path):
        """列出本地目录内容"""
        return self._storage.listdir(path)

    def path(self, name):
        """获取本地文件完整路径"""
        return self._storage.path(name)


# 全局存储后端实例（默认使用本地存储）
_storage_backend = None


def get_storage_backend():
    """获取全局存储后端实例"""
    global _storage_backend
    if _storage_backend is None:
        from django.conf import settings
        _storage_backend = LocalStorageBackend(
            location=getattr(settings, 'MEDIA_ROOT', None),
            base_url=getattr(settings, 'MEDIA_URL', None),
        )
    return _storage_backend
