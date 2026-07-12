"""
P14: 排序功能测试
- ProjectViewSet: 支持 created_at/updated_at/name/status/priority 排序
- TaskViewSet: 支持 created_at/updated_at/title/status/priority 排序
- FinanceExpenseViewSet: 支持 created_at/updated_at/title/amount 排序
- 支持升序（?ordering=field）和降序（?ordering=-field）
"""
from datetime import timedelta

import pytest
from django.utils import timezone


def get_results(response):
    """从分页响应中提取结果列表"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        data = data.get('data', data)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestProjectSorting:
    """项目列表排序测试"""

    def test_sort_by_name_asc(self, member_client, make_project):
        """按名称升序排序"""
        make_project(name='Bravo')
        make_project(name='Alpha')
        make_project(name='Charlie')
        resp = member_client.get('/api/v1/projects/?ordering=name')
        assert resp.status_code == 200
        names = [p['name'] for p in get_results(resp)]
        assert names == ['Alpha', 'Bravo', 'Charlie']

    def test_sort_by_name_desc(self, member_client, make_project):
        """按名称降序排序"""
        make_project(name='Bravo')
        make_project(name='Alpha')
        make_project(name='Charlie')
        resp = member_client.get('/api/v1/projects/?ordering=-name')
        assert resp.status_code == 200
        names = [p['name'] for p in get_results(resp)]
        assert names == ['Charlie', 'Bravo', 'Alpha']

    def test_sort_by_status(self, member_client, make_project):
        """按状态排序（active < closed）"""
        make_project(name='P1', status='closed')
        make_project(name='P2', status='active')
        resp = member_client.get('/api/v1/projects/?ordering=status')
        assert resp.status_code == 200
        results = get_results(resp)
        # active 字典序在 closed 之前
        assert results[0]['status'] == 'active'
        assert results[1]['status'] == 'closed'

    def test_sort_by_priority(self, member_client, make_project):
        """按优先级排序（high < normal < urgent）"""
        make_project(name='P1', priority='urgent')
        make_project(name='P2', priority='high')
        make_project(name='P3', priority='normal')
        resp = member_client.get('/api/v1/projects/?ordering=priority')
        assert resp.status_code == 200
        results = get_results(resp)
        priorities = [p['priority'] for p in results]
        assert priorities == ['high', 'normal', 'urgent']

    def test_sort_by_created_at_desc(self, member_client, make_project):
        """按创建时间降序（默认排序）"""
        p1 = make_project(name='First')
        p2 = make_project(name='Second')
        p3 = make_project(name='Third')
        # 显式设置不同的创建时间，避免时间戳相同导致顺序不确定
        base = timezone.now()
        p1.created_at = base - timedelta(minutes=3)
        p1.save(update_fields=['created_at'])
        p2.created_at = base - timedelta(minutes=2)
        p2.save(update_fields=['created_at'])
        p3.created_at = base - timedelta(minutes=1)
        p3.save(update_fields=['created_at'])
        resp = member_client.get('/api/v1/projects/?ordering=-created_at')
        assert resp.status_code == 200
        names = [p['name'] for p in get_results(resp)]
        # 最晚创建的在前
        assert names[0] == 'Third'
        assert names[-1] == 'First'

    def test_sort_by_updated_at(self, member_client, make_project):
        """按更新时间排序"""
        from apps.projects.models import Project
        p1 = make_project(name='Old')
        p2 = make_project(name='New')
        # 使用 queryset.update 绕过 auto_now，显式设置不同的更新时间
        base = timezone.now()
        Project.objects.filter(pk=p1.pk).update(updated_at=base + timedelta(minutes=2))
        Project.objects.filter(pk=p2.pk).update(updated_at=base + timedelta(minutes=1))
        resp = member_client.get('/api/v1/projects/?ordering=-updated_at')
        assert resp.status_code == 200
        names = [p['name'] for p in get_results(resp)]
        # p1 的 updated_at 更大，应排在前面
        assert names[0] == 'Old'


@pytest.mark.api
@pytest.mark.django_db
class TestTaskSorting:
    """任务列表排序测试"""

    def test_sort_by_title_asc(self, member_client, make_task):
        """按标题升序排序"""
        make_task(title='Task C')
        make_task(title='Task A')
        make_task(title='Task B')
        resp = member_client.get('/api/v1/tasks/?ordering=title')
        assert resp.status_code == 200
        titles = [t['title'] for t in get_results(resp)]
        assert titles == ['Task A', 'Task B', 'Task C']

    def test_sort_by_title_desc(self, member_client, make_task):
        """按标题降序排序"""
        make_task(title='Task C')
        make_task(title='Task A')
        make_task(title='Task B')
        resp = member_client.get('/api/v1/tasks/?ordering=-title')
        assert resp.status_code == 200
        titles = [t['title'] for t in get_results(resp)]
        assert titles == ['Task C', 'Task B', 'Task A']

    def test_sort_by_status(self, member_client, make_task):
        """按状态排序"""
        make_task(title='T1', status='done')
        make_task(title='T2', status='todo')
        resp = member_client.get('/api/v1/tasks/?ordering=status')
        assert resp.status_code == 200
        results = get_results(resp)
        # done 字典序在 todo 之前
        assert results[0]['status'] == 'done'
        assert results[1]['status'] == 'todo'

    def test_sort_by_priority(self, member_client, make_task):
        """按优先级排序"""
        make_task(title='T1', priority='urgent')
        make_task(title='T2', priority='low')
        make_task(title='T3', priority='high')
        resp = member_client.get('/api/v1/tasks/?ordering=priority')
        assert resp.status_code == 200
        results = get_results(resp)
        priorities = [t['priority'] for t in results]
        # low < urgent? 字典序: high < low < urgent
        assert priorities == ['high', 'low', 'urgent']

    def test_sort_by_created_at_desc(self, member_client, make_task):
        """按创建时间降序"""
        t1 = make_task(title='First')
        t2 = make_task(title='Second')
        t3 = make_task(title='Third')
        # 显式设置不同的创建时间，避免时间戳相同导致顺序不确定
        base = timezone.now()
        t1.created_at = base - timedelta(minutes=3)
        t1.save(update_fields=['created_at'])
        t2.created_at = base - timedelta(minutes=2)
        t2.save(update_fields=['created_at'])
        t3.created_at = base - timedelta(minutes=1)
        t3.save(update_fields=['created_at'])
        resp = member_client.get('/api/v1/tasks/?ordering=-created_at')
        assert resp.status_code == 200
        titles = [t['title'] for t in get_results(resp)]
        assert titles[0] == 'Third'
        assert titles[-1] == 'First'


@pytest.mark.api
@pytest.mark.django_db
class TestFinanceSorting:
    """经费明细列表排序测试"""

    def test_sort_by_amount_asc(self, member_client, make_finance):
        """按金额升序排序"""
        make_finance(amount=300, title='F3')
        make_finance(amount=100, title='F1')
        make_finance(amount=200, title='F2')
        resp = member_client.get('/api/v1/finance/expenses/?ordering=amount')
        assert resp.status_code == 200
        results = get_results(resp)
        amounts = [float(r['amount']) for r in results]
        assert amounts == [100.0, 200.0, 300.0]

    def test_sort_by_amount_desc(self, member_client, make_finance):
        """按金额降序排序"""
        make_finance(amount=300, title='F3')
        make_finance(amount=100, title='F1')
        make_finance(amount=200, title='F2')
        resp = member_client.get('/api/v1/finance/expenses/?ordering=-amount')
        assert resp.status_code == 200
        results = get_results(resp)
        amounts = [float(r['amount']) for r in results]
        assert amounts == [300.0, 200.0, 100.0]

    def test_sort_by_title_asc(self, member_client, make_finance):
        """按标题升序排序"""
        make_finance(amount=100, title='Charlie')
        make_finance(amount=100, title='Alpha')
        make_finance(amount=100, title='Bravo')
        resp = member_client.get('/api/v1/finance/expenses/?ordering=title')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(resp)]
        assert titles == ['Alpha', 'Bravo', 'Charlie']

    def test_sort_by_created_at_desc(self, member_client, make_finance):
        """按创建时间降序"""
        f1 = make_finance(amount=100, title='First')
        f2 = make_finance(amount=100, title='Second')
        f3 = make_finance(amount=100, title='Third')
        # 显式设置不同的创建时间，避免时间戳相同导致顺序不确定
        base = timezone.now()
        f1.created_at = base - timedelta(minutes=3)
        f1.save(update_fields=['created_at'])
        f2.created_at = base - timedelta(minutes=2)
        f2.save(update_fields=['created_at'])
        f3.created_at = base - timedelta(minutes=1)
        f3.save(update_fields=['created_at'])
        resp = member_client.get('/api/v1/finance/expenses/?ordering=-created_at')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(resp)]
        assert titles[0] == 'Third'
        assert titles[-1] == 'First'
