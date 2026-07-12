"""
N08 统一待办模块测试
- 聚合待处理任务、逾期任务、待审批申请、待审核贡献
- 权限：需要认证
"""
from datetime import timedelta
import pytest

from django.utils import timezone

TODO_URL = '/api/v1/todo/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestUnifiedTodoAPI:
    """统一待办 API 测试"""

    def test_member_gets_pending_tasks(self, member_client, make_task):
        """成员获取分配给自己的待处理任务"""
        make_task(assignee=member_client.user, title='我的待办', status='todo')
        resp = member_client.get(TODO_URL)
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        results = data['results']
        task_items = [t for t in results if t['type'] == 'task']
        assert any(t['title'] == '我的待办' for t in task_items)

    def test_done_tasks_excluded(self, member_client, make_task):
        """已完成任务不计入待办"""
        make_task(assignee=member_client.user, title='已完成任务', status='done')
        resp = member_client.get(TODO_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert not any(t.get('title') == '已完成任务' for t in results)

    def test_others_tasks_excluded(self, member_client, make_task, make_user):
        """不获取分配给他人的任务"""
        other = make_user(email='other_todo@test.com')
        make_task(assignee=other, title='他人任务', status='todo')
        resp = member_client.get(TODO_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert not any(t.get('title') == '他人任务' for t in results)

    def test_overdue_task_type(self, member_client, make_task):
        """逾期任务标记为 overdue_task 类型"""
        past = timezone.now() - timedelta(days=1)
        make_task(
            assignee=member_client.user,
            title='逾期任务',
            status='todo',
            deadline=past,
        )
        resp = member_client.get(TODO_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        overdue_items = [t for t in results if t['type'] == 'overdue_task']
        assert any(t['title'] == '逾期任务' for t in overdue_items)

    def test_approver_gets_pending_approvals(self, approver_client, make_sensitive_data, make_user):
        """审批人获取待审批的敏感资料申请"""
        applicant = make_user(email='todo_applicant@test.com')
        sd = make_sensitive_data()
        from apps.sensitive.models import SensitiveAccessRequest
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            reason='需要查看',
            status=SensitiveAccessRequest.Status.PENDING,
        )
        resp = approver_client.get(TODO_URL)
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        results = data['results']
        approval_items = [t for t in results if t['type'] == 'approval']
        assert len(approval_items) >= 1

    def test_teacher_gets_contribution_reviews(self, teacher_client, make_user, make_project):
        """老师获取待审核的贡献记录"""
        contributor = make_user(email='todo_contrib@test.com')
        project = make_project()
        from apps.contributions.models import Contribution
        Contribution.objects.create(
            user=contributor,
            project=project,
            contribution_type=Contribution.ContributionType.TASK_COMPLETE,
            content='完成测试任务',
            status=Contribution.Status.PENDING,
        )
        resp = teacher_client.get(TODO_URL)
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        results = data['results']
        review_items = [t for t in results if t['type'] == 'contribution_review']
        assert len(review_items) >= 1

    def test_member_no_approvals(self, member_client, make_sensitive_data, make_user):
        """普通成员不获取待审批申请"""
        applicant = make_user(email='todo_app2@test.com')
        sd = make_sensitive_data()
        from apps.sensitive.models import SensitiveAccessRequest
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            reason='需要查看',
            status=SensitiveAccessRequest.Status.PENDING,
        )
        resp = member_client.get(TODO_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert not any(t['type'] == 'approval' for t in results)

    def test_unauthenticated_rejected(self, api_client):
        """未认证用户被拒绝"""
        resp = api_client.get(TODO_URL)
        assert resp.status_code in (401, 403)

    def test_todo_has_unified_fields(self, member_client, make_task):
        """待办项包含统一字段 type/title/url/priority/due_date"""
        make_task(assignee=member_client.user, title='字段检查', status='todo')
        resp = member_client.get(TODO_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert len(results) > 0
        item = results[0]
        for field in ('type', 'title', 'url', 'priority', 'due_date'):
            assert field in item, f'缺少字段 {field}'

    def test_filter_by_type_task(self, member_client, make_task):
        """按 type=task 筛选只返回任务类型"""
        make_task(assignee=member_client.user, title='普通任务', status='todo')
        resp = member_client.get(f'{TODO_URL}?type=task')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert all(t['type'] == 'task' for t in results)

    def test_filter_by_type_approval(self, approver_client, make_sensitive_data, make_user):
        """按 type=approval 筛选只返回审批类型"""
        applicant = make_user(email='filter_approvals@test.com')
        sd = make_sensitive_data()
        from apps.sensitive.models import SensitiveAccessRequest
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            reason='需要查看',
            status=SensitiveAccessRequest.Status.PENDING,
        )
        resp = approver_client.get(f'{TODO_URL}?type=approval')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert len(results) >= 1
        assert all(t['type'] == 'approval' for t in results)

    def test_filter_by_type_contribution_review(self, teacher_client, make_user, make_project):
        """按 type=contribution_review 筛选只返回贡献审核类型"""
        contributor = make_user(email='filter_contrib@test.com')
        project = make_project()
        from apps.contributions.models import Contribution
        Contribution.objects.create(
            user=contributor,
            project=project,
            contribution_type=Contribution.ContributionType.TASK_COMPLETE,
            content='完成测试任务',
            status=Contribution.Status.PENDING,
        )
        resp = teacher_client.get(f'{TODO_URL}?type=contribution_review')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data['results']
        assert len(results) >= 1
        assert all(t['type'] == 'contribution_review' for t in results)
