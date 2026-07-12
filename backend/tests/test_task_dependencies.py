"""
N03 任务依赖关系模块测试
- 创建 / 列表 / 删除
- 禁止自依赖、禁止循环依赖
- 权限：普通成员只读
"""
import pytest

from django.core.exceptions import ValidationError

from apps.tasks.dependency_models import TaskDependency

DEP_URL = '/api/v1/tasks/dependencies/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def extract_results(resp):
    data = extract_data(resp)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestTaskDependencyAPI:
    """任务依赖关系 API 测试"""

    def test_create_dependency(self, teacher_client, make_task):
        """老师可以创建依赖关系"""
        t1 = make_task()
        t2 = make_task()
        resp = teacher_client.post(DEP_URL, {
            'task': t1.id,
            'depends_on': t2.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['task'] == t1.id
        assert data['depends_on'] == t2.id

    def test_prevent_self_dependency(self, teacher_client, make_task):
        """禁止自依赖"""
        t1 = make_task()
        resp = teacher_client.post(DEP_URL, {
            'task': t1.id,
            'depends_on': t1.id,
        }, format='json')
        assert resp.status_code == 400, resp.json()

    def test_prevent_circular_dependency(self, teacher_client, make_task):
        """禁止循环依赖：A->B 后不能 B->A"""
        t1 = make_task()
        t2 = make_task()
        # 创建 t1 -> t2
        resp1 = teacher_client.post(DEP_URL, {
            'task': t1.id, 'depends_on': t2.id,
        }, format='json')
        assert resp1.status_code in (200, 201)
        # 尝试创建 t2 -> t1（形成环）
        resp2 = teacher_client.post(DEP_URL, {
            'task': t2.id, 'depends_on': t1.id,
        }, format='json')
        assert resp2.status_code == 400, resp2.json()

    def test_prevent_indirect_circular(self, teacher_client, make_task):
        """禁止间接循环依赖：A->B, B->C 后不能 C->A"""
        t1 = make_task()
        t2 = make_task()
        t3 = make_task()
        teacher_client.post(DEP_URL, {'task': t1.id, 'depends_on': t2.id}, format='json')
        teacher_client.post(DEP_URL, {'task': t2.id, 'depends_on': t3.id}, format='json')
        # t3 -> t1 会形成环 t1->t2->t3->t1
        resp = teacher_client.post(DEP_URL, {
            'task': t3.id, 'depends_on': t1.id,
        }, format='json')
        assert resp.status_code == 400, resp.json()

    def test_list_dependencies(self, member_client, make_task):
        """普通成员可以查看依赖列表"""
        t1 = make_task()
        t2 = make_task()
        TaskDependency.objects.create(task=t1, depends_on=t2)
        resp = member_client.get(DEP_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_delete_dependency(self, teacher_client, make_task):
        """老师可以删除依赖关系"""
        t1 = make_task()
        t2 = make_task()
        dep = TaskDependency.objects.create(task=t1, depends_on=t2)
        resp = teacher_client.delete(f'{DEP_URL}{dep.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not TaskDependency.objects.filter(id=dep.id).exists()

    def test_member_cannot_create_dependency(self, member_client, make_task):
        """普通成员不能创建依赖关系"""
        t1 = make_task()
        t2 = make_task()
        resp = member_client.post(DEP_URL, {
            'task': t1.id, 'depends_on': t2.id,
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestTaskDependencyModel:
    """任务依赖关系模型测试"""

    def test_unique_together(self, make_task):
        """同一对 (task, depends_on) 唯一"""
        t1 = make_task()
        t2 = make_task()
        TaskDependency.objects.create(task=t1, depends_on=t2)
        with pytest.raises(Exception):
            TaskDependency.objects.create(task=t1, depends_on=t2)

    def test_self_dependency_raises(self, make_task):
        """模型层禁止自依赖"""
        t1 = make_task()
        with pytest.raises(ValidationError):
            TaskDependency.objects.create(task=t1, depends_on=t1)

    def test_related_names(self, make_task):
        """反向关系 dependencies / dependents"""
        t1 = make_task()
        t2 = make_task()
        TaskDependency.objects.create(task=t1, depends_on=t2)
        assert t1.dependencies.count() == 1
        assert t2.dependents.count() == 1
