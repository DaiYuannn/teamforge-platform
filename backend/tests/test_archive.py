"""
P13: 项目归档测试
- archived_at 字段：项目状态变为 closed 时自动设置
- 取消归档：状态从 closed 变为其他时自动清除 archived_at
- is_archived 属性
- 通过 API 和阶段推进触发归档
"""
import pytest

from apps.projects.models import Project


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.model
@pytest.mark.django_db
class TestArchiveModel:
    """Project 归档模型逻辑测试"""

    def test_active_project_not_archived(self, make_project):
        """进行中的项目 archived_at 为空"""
        project = make_project(status='active')
        assert project.archived_at is None
        assert project.is_archived is False

    def test_status_to_closed_sets_archived_at(self, make_project):
        """状态变为 closed 时自动设置 archived_at"""
        project = make_project(status='active')
        assert project.archived_at is None

        project.status = Project.Status.CLOSED
        project.save()

        project.refresh_from_db()
        assert project.archived_at is not None
        assert project.is_archived is True

    def test_reopen_clears_archived_at(self, make_project):
        """状态从 closed 变回 active 时清除 archived_at"""
        project = make_project(status='active')
        project.status = Project.Status.CLOSED
        project.save()
        project.refresh_from_db()
        assert project.archived_at is not None

        project.status = Project.Status.ACTIVE
        project.save()
        project.refresh_from_db()
        assert project.archived_at is None
        assert project.is_archived is False

    def test_closed_on_create_sets_archived_at(self, make_project):
        """创建时即为 closed 状态也设置 archived_at"""
        project = make_project(status='closed')
        assert project.archived_at is not None
        assert project.is_archived is True

    def test_archived_at_not_overwritten(self, make_project):
        """已设置的 archived_at 不会被覆盖"""
        project = make_project(status='active')
        project.status = Project.Status.CLOSED
        project.save()
        project.refresh_from_db()
        first_archived = project.archived_at

        # 再次保存（状态仍为 closed）
        project.intro = '更新简介'
        project.save()
        project.refresh_from_db()
        assert project.archived_at == first_archived

    def test_paused_does_not_archive(self, make_project):
        """暂停状态不触发归档"""
        project = make_project(status='active')
        project.status = Project.Status.PAUSED
        project.save()
        project.refresh_from_db()
        assert project.archived_at is None
        assert project.is_archived is False


@pytest.mark.api
@pytest.mark.django_db
class TestArchiveAPI:
    """项目归档 API 测试"""

    def test_archive_via_api(self, admin_client, make_project):
        """通过 API 将项目状态改为 closed 触发归档"""
        project = make_project(status='active')
        resp = admin_client.patch(f'/api/v1/projects/{project.id}/', {
            'status': 'closed',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'closed'
        assert data['archived_at'] is not None
        assert data['is_archived'] is True

        project.refresh_from_db()
        assert project.archived_at is not None

    def test_unarchive_via_api(self, admin_client, make_project):
        """通过 API 将项目从 closed 改回 active 取消归档"""
        project = make_project(status='closed')
        # 确认已归档
        project.refresh_from_db()
        assert project.archived_at is not None

        resp = admin_client.patch(f'/api/v1/projects/{project.id}/', {
            'status': 'active',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'active'
        assert data['archived_at'] is None
        assert data['is_archived'] is False

    def test_list_shows_archived_field(self, admin_client, make_project):
        """列表接口包含归档字段"""
        make_project(status='closed', name='已归档项目')
        make_project(status='active', name='活跃项目')
        resp = admin_client.get('/api/v1/projects/')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) == 2
        archived = [r for r in results if r.get('is_archived') is True]
        active = [r for r in results if r.get('is_archived') is False]
        assert len(archived) == 1
        assert len(active) == 1


@pytest.mark.api
@pytest.mark.django_db
class TestArchiveViaStage:
    """通过阶段推进触发归档（advance_stage 到 CLOSED 阶段）"""

    def test_advance_to_closed_stage_archives(self, admin_client, make_project):
        """推进到「已结项」阶段(14)自动设置 status=closed 并归档"""
        project = make_project(status='active', current_stage=1)
        # 负责人为 admin，便于操作
        project.leader = admin_client.user
        project.save()

        resp = admin_client.post(f'/api/v1/projects/{project.id}/stage/', {
            'to_stage': Project.Stage.CLOSED,
            'note': '结项',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'closed'
        assert data['archived_at'] is not None
        assert data['is_archived'] is True
