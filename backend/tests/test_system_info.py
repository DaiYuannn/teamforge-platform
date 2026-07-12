"""
P19 Git 与版本管理测试
- 系统信息接口返回版本号、Git 分支、Django 版本、已安装应用数量
- VERSION 文件存在并可读取
- 权限校验（老师/管理员）
"""
import os

import django
import pytest
from django.conf import settings


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestVersionFile:
    """VERSION 文件测试"""

    def test_version_file_exists(self):
        """VERSION 文件存在于项目根目录"""
        version_path = settings.BASE_DIR / 'VERSION'
        assert version_path.exists(), 'VERSION 文件不存在'

    def test_version_file_has_version(self):
        """VERSION 文件包含 VERSION 字段"""
        version_path = settings.BASE_DIR / 'VERSION'
        content = version_path.read_text(encoding='utf-8')
        assert 'VERSION=' in content
        # 提取版本号
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('VERSION='):
                version = line.split('=', 1)[1].strip()
                assert version, '版本号不能为空'
                assert version != 'unknown'
                break


@pytest.mark.api
@pytest.mark.django_db
class TestSystemInfoEndpoint:
    """系统信息接口测试"""

    def test_system_info_returns_fields(self, teacher_client):
        """系统信息接口返回必需字段"""
        resp = teacher_client.get('/api/v1/dashboard/system-info/')
        assert resp.status_code == 200
        data = extract_data(resp)
        for key in ('version', 'git_branch', 'django_version', 'installed_apps_count'):
            assert key in data, f'缺失字段 {key}'

    def test_version_matches_file(self, teacher_client):
        """返回的版本号与 VERSION 文件一致"""
        resp = teacher_client.get('/api/v1/dashboard/system-info/')
        data = extract_data(resp)
        version_path = settings.BASE_DIR / 'VERSION'
        expected = 'unknown'
        if version_path.exists():
            for line in version_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith('VERSION='):
                    expected = line.split('=', 1)[1].strip()
                    break
        assert data['version'] == expected

    def test_django_version(self, teacher_client):
        """返回的 Django 版本与实际一致"""
        resp = teacher_client.get('/api/v1/dashboard/system-info/')
        data = extract_data(resp)
        assert data['django_version'] == django.get_version()

    def test_installed_apps_count(self, teacher_client):
        """返回的已安装应用数量与 settings 一致"""
        resp = teacher_client.get('/api/v1/dashboard/system-info/')
        data = extract_data(resp)
        assert data['installed_apps_count'] == len(settings.INSTALLED_APPS)
        assert data['installed_apps_count'] > 0

    def test_git_branch_value(self, teacher_client):
        """Git 分支字段存在（可能为 None 或字符串）"""
        resp = teacher_client.get('/api/v1/dashboard/system-info/')
        data = extract_data(resp)
        # git_branch 可能为 None（无 git 环境）或分支名字符串
        assert 'git_branch' in data
        if data['git_branch'] is not None:
            assert isinstance(data['git_branch'], str)
            assert len(data['git_branch']) > 0


@pytest.mark.api
@pytest.mark.django_db
class TestSystemInfoPermission:
    """系统信息接口权限测试"""

    def test_admin_can_access(self, admin_client):
        """管理员可访问"""
        resp = admin_client.get('/api/v1/dashboard/system-info/')
        assert resp.status_code == 200

    def test_member_forbidden(self, member_client):
        """普通成员不可访问"""
        resp = member_client.get('/api/v1/dashboard/system-info/')
        assert resp.status_code == 403

    def test_unauthenticated_forbidden(self, api_client):
        """未登录不可访问"""
        resp = api_client.get('/api/v1/dashboard/system-info/')
        assert resp.status_code == 401
