"""
N56: CI 配置测试
- 验证 .github/workflows/ci.yml 存在
- 验证后端：lint (flake8) / test (pytest) / check (manage.py check)
- 验证前端：lint / type-check (vue-tsc) / test (vitest) / build
"""
from pathlib import Path

import pytest
from django.conf import settings


def _ci_path():
    """CI 配置文件路径（仓库根目录 .github/workflows/ci.yml）"""
    # settings.BASE_DIR 为 backend 目录，其上一级为仓库根目录
    repo_root = Path(settings.BASE_DIR).parent
    return repo_root / '.github' / 'workflows' / 'ci.yml'


def _ci_content():
    path = _ci_path()
    assert path.exists(), f'CI 配置文件不存在: {path}'
    return path.read_text(encoding='utf-8')


@pytest.mark.api
class TestCIConfig:
    """CI 配置文件测试"""

    def test_ci_file_exists(self):
        """CI 配置文件存在"""
        assert _ci_path().exists(), '.github/workflows/ci.yml 不存在'

    def test_ci_has_backend_job(self):
        """CI 包含后端任务"""
        content = _ci_content()
        assert 'backend' in content.lower()
        assert 'python' in content.lower()

    def test_ci_backend_flake8_lint(self):
        """后端包含 flake8 lint 步骤"""
        content = _ci_content()
        assert 'flake8' in content
        assert 'lint' in content.lower()

    def test_ci_backend_pytest_test(self):
        """后端包含 pytest 测试步骤"""
        content = _ci_content()
        assert 'pytest' in content

    def test_ci_backend_manage_check(self):
        """后端包含 manage.py check 步骤"""
        content = _ci_content()
        assert 'manage.py check' in content or 'manage.py' in content and 'check' in content

    def test_ci_has_frontend_job(self):
        """CI 包含前端任务"""
        content = _ci_content()
        assert 'frontend' in content.lower()
        assert 'node' in content.lower()

    def test_ci_frontend_lint(self):
        """前端包含 lint 步骤"""
        content = _ci_content()
        assert 'npm run lint' in content

    def test_ci_frontend_type_check(self):
        """前端包含 vue-tsc type-check 步骤"""
        content = _ci_content()
        assert 'type-check' in content or 'vue-tsc' in content

    def test_ci_frontend_test(self):
        """前端包含 vitest 测试步骤"""
        content = _ci_content()
        assert 'npm run test' in content or 'vitest' in content

    def test_ci_frontend_build(self):
        """前端包含 build 步骤"""
        content = _ci_content()
        assert 'npm run build' in content or 'vite build' in content
