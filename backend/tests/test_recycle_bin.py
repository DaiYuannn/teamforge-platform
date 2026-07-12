"""
回收站（软删除）模块测试
覆盖：
- 软删除（API + 模型层）：is_deleted=True、deleted_at、deleted_by
- 回收站列表
- 恢复
- 永久删除
- 普通查询排除已软删除对象
- 权限校验
- 任务 / 经费明细软删除
"""
import pytest

from apps.projects.models import Project
from apps.tasks.models import Task
from apps.finance.models import FinanceExpense


def extract_data(response):
    """从统一响应中取出 data 字段"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


# ========== 模型层：软删除字段与默认管理器 ==========

@pytest.mark.model
@pytest.mark.django_db
class TestSoftDeleteModel:
    """模型层软删除行为"""

    def test_default_manager_excludes_soft_deleted(self, make_project):
        """默认管理器 objects 排除已软删除对象"""
        p1 = make_project(code='P-001')
        p2 = make_project(code='P-002')
        # 软删除 p1
        p1.soft_delete()
        codes = list(Project.objects.values_list('code', flat=True))
        assert 'P-001' not in codes
        assert 'P-002' in codes

    def test_all_objects_includes_soft_deleted(self, make_project):
        """all_objects 管理器包含已软删除对象"""
        p1 = make_project(code='P-ALL-1')
        p1.soft_delete()
        codes = list(Project.all_objects.values_list('code', flat=True))
        assert 'P-ALL-1' in codes
        # 普通管理器不含
        assert 'P-ALL-1' not in list(Project.objects.values_list('code', flat=True))

    def test_soft_delete_sets_fields(self, make_project, make_user):
        """soft_delete 设置 is_deleted / deleted_at / deleted_by"""
        user = make_user(email='deleter@test.com', global_role='teacher')
        project = make_project(code='P-SD-1')
        assert project.is_deleted is False
        assert project.deleted_at is None
        project.soft_delete(user=user)
        project.refresh_from_db()
        assert project.is_deleted is True
        assert project.deleted_at is not None
        assert project.deleted_by_id == user.id

    def test_restore_clears_fields(self, make_project):
        """restore 清除软删除标记"""
        project = make_project(code='P-RS-1')
        project.soft_delete()
        project.restore()
        project.refresh_from_db()
        assert project.is_deleted is False
        assert project.deleted_at is None
        assert project.deleted_by is None
        # 恢复后应重新出现在默认管理器中
        assert Project.objects.filter(code='P-RS-1').exists()

    def test_new_object_not_deleted_by_default(self, make_project):
        """新建对象默认 is_deleted=False，出现在默认管理器"""
        project = make_project(code='P-NEW-1')
        assert project.is_deleted is False
        assert Project.objects.filter(id=project.id).exists()


# ========== API 层：软删除 + 回收站 ==========

@pytest.mark.api
@pytest.mark.django_db
class TestRecycleBinAPI:
    """回收站 API 测试"""

    # ---- 软删除（DELETE 走软删除） ----
    def test_delete_project_is_soft_delete(self, teacher_client, make_project):
        """DELETE 项目接口执行软删除而非物理删除"""
        project = make_project(code='API-SD-1')
        resp = teacher_client.delete(f'/api/v1/projects/{project.id}/')
        assert resp.status_code in (200, 204), resp.json()
        # 数据库中仍存在，但被标记为已删除
        deleted = Project.all_objects.get(id=project.id)
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None
        assert deleted.deleted_by_id == teacher_client.user.id

    def test_soft_deleted_excluded_from_project_list(self, teacher_client, make_project):
        """普通查询排除已软删除的项目"""
        p1 = make_project(code='LIST-1')
        p2 = make_project(code='LIST-2')
        teacher_client.delete(f'/api/v1/projects/{p1.id}/')
        # 使用同一个 client 查询列表（避免共享 api_client 凭证覆盖）
        resp = teacher_client.get('/api/v1/projects/')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        codes = [r.get('code') for r in results]
        assert 'LIST-1' not in codes
        assert 'LIST-2' in codes

    def test_soft_deleted_not_retrievable(self, teacher_client, make_project):
        """已软删除的项目在普通接口不可访问"""
        project = make_project(code='RETR-1')
        teacher_client.delete(f'/api/v1/projects/{project.id}/')
        # 使用同一个 client 查询详情
        resp = teacher_client.get(f'/api/v1/projects/{project.id}/')
        assert resp.status_code == 404

    # ---- 回收站列表 ----
    def test_list_recycle_bin_project(self, teacher_client, make_project):
        """GET 回收站列表返回已软删除的项目"""
        p1 = make_project(code='RB-1')
        make_project(code='RB-2')  # 未删除，不应出现
        teacher_client.delete(f'/api/v1/projects/{p1.id}/')

        resp = teacher_client.get('/api/v1/recycle-bin/?type=project')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        codes = [r.get('code') for r in data]
        assert 'RB-1' in codes
        assert 'RB-2' not in codes

    def test_list_recycle_bin_default_type_is_project(self, teacher_client, make_project):
        """未指定 type 时默认为 project"""
        p1 = make_project(code='DEF-1')
        teacher_client.delete(f'/api/v1/projects/{p1.id}/')
        resp = teacher_client.get('/api/v1/recycle-bin/')
        assert resp.status_code == 200
        data = extract_data(resp)
        codes = [r.get('code') for r in data]
        assert 'DEF-1' in codes

    def test_list_recycle_bin_invalid_type(self, admin_client):
        """无效 type 返回 400"""
        resp = admin_client.get('/api/v1/recycle-bin/?type=unknown')
        assert resp.status_code == 400

    # ---- 恢复 ----
    def test_restore_project(self, teacher_client, make_project):
        """POST 恢复项目"""
        project = make_project(code='RESTORE-1')
        teacher_client.delete(f'/api/v1/projects/{project.id}/')  # 软删除
        assert not Project.objects.filter(id=project.id).exists()

        resp = teacher_client.post('/api/v1/recycle-bin/', {
            'type': 'project',
            'id': project.id,
        }, format='json')
        assert resp.status_code == 200, resp.json()

        # 恢复后重新出现在默认管理器
        restored = Project.objects.get(id=project.id)
        assert restored.is_deleted is False
        assert restored.deleted_at is None

    def test_restore_not_in_recycle_bin(self, teacher_client, make_project):
        """恢复未删除的对象返回 404"""
        project = make_project(code='RESTORE-404')
        resp = teacher_client.post('/api/v1/recycle-bin/', {
            'type': 'project',
            'id': project.id,
        }, format='json')
        assert resp.status_code == 404

    def test_restore_missing_id(self, teacher_client, make_project):
        """恢复缺少 id 返回错误"""
        make_project(code='RESTORE-NOID')
        resp = teacher_client.post('/api/v1/recycle-bin/', {
            'type': 'project',
        }, format='json')
        assert resp.status_code == 400

    # ---- 永久删除 ----
    def test_permanent_delete_project(self, admin_client, make_project):
        """DELETE 永久删除项目（物理删除）"""
        project = make_project(code='PERM-1')
        # 先软删除进入回收站
        admin_client.delete(f'/api/v1/projects/{project.id}/')
        assert Project.all_objects.filter(id=project.id).exists()

        resp = admin_client.delete(f'/api/v1/recycle-bin/?type=project&id={project.id}')
        assert resp.status_code == 200, resp.json()
        # 物理删除后不存在
        assert not Project.all_objects.filter(id=project.id).exists()

    def test_permanent_delete_not_in_recycle_bin(self, admin_client, make_project):
        """永久删除未在回收站的对象返回 404"""
        project = make_project(code='PERM-404')
        resp = admin_client.delete(f'/api/v1/recycle-bin/?type=project&id={project.id}')
        assert resp.status_code == 404

    # ---- 任务 / 经费明细软删除 ----
    def test_delete_task_is_soft_delete(self, teacher_client, make_task):
        """删除任务为软删除"""
        task = make_task(title='TASK-SD-1')
        resp = teacher_client.delete(f'/api/v1/tasks/{task.id}/')
        assert resp.status_code in (200, 204), resp.json()
        deleted = Task.all_objects.get(id=task.id)
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None

    def test_list_recycle_bin_task(self, teacher_client, make_task):
        """回收站列表支持任务类型"""
        task = make_task(title='TASK-RB-1')
        teacher_client.delete(f'/api/v1/tasks/{task.id}/')
        resp = teacher_client.get('/api/v1/recycle-bin/?type=task')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        titles = [r.get('title') for r in data]
        assert 'TASK-RB-1' in titles

    def test_restore_task(self, teacher_client, make_task):
        """恢复任务"""
        task = make_task(title='TASK-RST-1')
        teacher_client.delete(f'/api/v1/tasks/{task.id}/')
        resp = teacher_client.post('/api/v1/recycle-bin/', {
            'type': 'task', 'id': task.id,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        assert Task.objects.filter(id=task.id).exists()

    def test_delete_finance_is_soft_delete(self, teacher_client, make_finance):
        """删除经费明细为软删除"""
        expense = make_finance(title='FIN-SD-1')
        resp = teacher_client.delete(f'/api/v1/finance/expenses/{expense.id}/')
        assert resp.status_code in (200, 204), resp.json()
        deleted = FinanceExpense.all_objects.get(id=expense.id)
        assert deleted.is_deleted is True

    def test_list_recycle_bin_finance(self, teacher_client, make_finance):
        """回收站列表支持经费明细类型"""
        expense = make_finance(title='FIN-RB-1')
        teacher_client.delete(f'/api/v1/finance/expenses/{expense.id}/')
        resp = teacher_client.get('/api/v1/recycle-bin/?type=finance_expense')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        titles = [r.get('title') for r in data]
        assert 'FIN-RB-1' in titles


# ========== 权限校验 ==========

@pytest.mark.permission
@pytest.mark.django_db
class TestRecycleBinPermissions:
    """回收站权限测试"""

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证用户无法访问回收站"""
        resp = api_client.get('/api/v1/recycle-bin/')
        assert resp.status_code == 401

    def test_member_can_list_recycle_bin(self, member_client):
        """普通成员可查看回收站列表"""
        resp = member_client.get('/api/v1/recycle-bin/?type=project')
        assert resp.status_code == 200

    def test_member_cannot_restore(self, member_client, make_project):
        """普通成员不能恢复（403）"""
        project = make_project(code='PERM-M-1')
        # 模型层直接软删除，避免在用例中同时使用两个 *_client（共享 api_client 会互相覆盖凭证）
        project.soft_delete()
        resp = member_client.post('/api/v1/recycle-bin/', {
            'type': 'project', 'id': project.id,
        }, format='json')
        assert resp.status_code == 403
        # 仍处于已删除状态
        assert Project.all_objects.get(id=project.id).is_deleted is True

    def test_teacher_can_restore(self, teacher_client, make_project):
        """老师可以恢复"""
        project = make_project(code='PERM-T-1')
        project.soft_delete()
        resp = teacher_client.post('/api/v1/recycle-bin/', {
            'type': 'project', 'id': project.id,
        }, format='json')
        assert resp.status_code == 200
        assert Project.objects.filter(id=project.id).exists()

    def test_member_cannot_permanent_delete(self, member_client, make_project):
        """普通成员不能永久删除（403）"""
        project = make_project(code='PERM-DEL-M-1')
        project.soft_delete()
        resp = member_client.delete(f'/api/v1/recycle-bin/?type=project&id={project.id}')
        assert resp.status_code == 403
        # 仍存在于回收站
        assert Project.all_objects.filter(id=project.id, is_deleted=True).exists()

    def test_teacher_cannot_permanent_delete(self, teacher_client, make_project):
        """老师不能永久删除（仅管理员，403）"""
        project = make_project(code='PERM-DEL-T-1')
        project.soft_delete()
        resp = teacher_client.delete(f'/api/v1/recycle-bin/?type=project&id={project.id}')
        assert resp.status_code == 403
        assert Project.all_objects.filter(id=project.id, is_deleted=True).exists()

    def test_admin_can_permanent_delete(self, admin_client, make_project):
        """管理员可以永久删除"""
        project = make_project(code='PERM-DEL-A-1')
        admin_client.delete(f'/api/v1/projects/{project.id}/')
        resp = admin_client.delete(f'/api/v1/recycle-bin/?type=project&id={project.id}')
        assert resp.status_code == 200
        assert not Project.all_objects.filter(id=project.id).exists()

    def test_member_cannot_delete_project(self, member_client, make_project):
        """普通成员不能删除项目（项目接口层权限，403）"""
        project = make_project(code='DEL-M-1')
        resp = member_client.delete(f'/api/v1/projects/{project.id}/')
        assert resp.status_code == 403
        # 未被软删除
        assert Project.objects.filter(id=project.id).exists()
