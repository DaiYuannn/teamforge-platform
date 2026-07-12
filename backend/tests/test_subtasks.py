"""
N01 子任务模块测试
- 创建 / 列表 / 筛选 / 更新 / 完成切换 / 删除
- 权限：普通成员只读，老师/管理员可写
"""
import pytest

from apps.tasks.subtask_models import SubTask

SUBTASK_URL = '/api/v1/tasks/subtasks/'


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
class TestSubTaskAPI:
    """子任务 API 测试"""

    def test_create_subtask_by_teacher(self, teacher_client, make_task):
        """老师可以创建子任务"""
        task = make_task()
        resp = teacher_client.post(SUBTASK_URL, {
            'parent': task.id,
            'title': '子任务1',
            'sort_order': 1,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == '子任务1'
        assert data['is_completed'] is False
        assert data['sort_order'] == 1

    def test_list_subtasks(self, member_client, make_task):
        """普通成员可以查看子任务列表"""
        task = make_task()
        SubTask.objects.create(parent=task, title='可见子任务')
        resp = member_client.get(SUBTASK_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_subtasks_by_parent(self, member_client, make_task):
        """按父任务筛选子任务"""
        task1 = make_task()
        task2 = make_task()
        SubTask.objects.create(parent=task1, title='A')
        SubTask.objects.create(parent=task2, title='B')
        resp = member_client.get(f'{SUBTASK_URL}?parent={task1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['parent'] == task1.id for r in results)
        assert any(r['title'] == 'A' for r in results)

    def test_update_subtask(self, teacher_client, make_task):
        """老师可以更新子任务"""
        task = make_task()
        st = SubTask.objects.create(parent=task, title='原标题')
        resp = teacher_client.patch(f'{SUBTASK_URL}{st.id}/', {
            'title': '新标题',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['title'] == '新标题'

    def test_toggle_subtask_complete(self, teacher_client, make_task):
        """切换子任务完成状态"""
        task = make_task()
        st = SubTask.objects.create(parent=task, title='待完成')
        assert st.is_completed is False
        resp = teacher_client.post(f'{SUBTASK_URL}{st.id}/toggle/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_completed'] is True
        assert data['completed_at'] is not None

    def test_toggle_subtask_incomplete(self, teacher_client, make_task):
        """切换已完成子任务为未完成"""
        task = make_task()
        st = SubTask.objects.create(parent=task, title='已完成', is_completed=True)
        resp = teacher_client.post(f'{SUBTASK_URL}{st.id}/toggle/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_completed'] is False

    def test_delete_subtask(self, teacher_client, make_task):
        """老师可以删除子任务"""
        task = make_task()
        st = SubTask.objects.create(parent=task, title='待删除')
        resp = teacher_client.delete(f'{SUBTASK_URL}{st.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not SubTask.objects.filter(id=st.id).exists()

    def test_member_cannot_create_subtask(self, member_client, make_task):
        """普通成员不能创建子任务"""
        task = make_task()
        resp = member_client.post(SUBTASK_URL, {
            'parent': task.id,
            'title': '成员尝试创建',
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestSubTaskModel:
    """子任务模型测试"""

    def test_default_values(self, make_task):
        """默认值：未完成、排序0"""
        st = SubTask.objects.create(parent=make_task(), title='默认')
        assert st.is_completed is False
        assert st.sort_order == 0
        assert st.completed_at is None

    def test_mark_completed_sets_time(self, make_task):
        """mark_completed 设置完成时间"""
        st = SubTask.objects.create(parent=make_task(), title='完成测试')
        st.mark_completed()
        assert st.is_completed is True
        assert st.completed_at is not None

    def test_related_name_subtasks(self, make_task):
        """反向关系 task.subtasks 可访问"""
        task = make_task()
        SubTask.objects.create(parent=task, title='反向关系')
        assert task.subtasks.count() == 1
