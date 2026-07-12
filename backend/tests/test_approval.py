"""
N41: 审批流程测试
- /api/v1/approvals/flows/      审批流程 CRUD
- /api/v1/approvals/requests/   审批申请 CRUD + approve/reject/cancel

注意：admin_client 与 member_client 共享同一 api_client 实例，同时使用会互相覆盖
凭证。因此需要“申请人”时使用 make_user 创建，仅用 admin_client 作为操作客户端。
"""
import pytest

from apps.common.approval_models import ApprovalFlow, ApprovalRequest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestApprovalFlow:
    """审批流程测试"""

    def test_create_flow(self, admin_client):
        """创建审批流程"""
        resp = admin_client.post('/api/v1/approvals/flows/', {
            'name': '请假流程', 'flow_type': 'leave',
            'steps': [{'name': '组长审批'}, {'name': '导师审批'}],
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        flow = ApprovalFlow.objects.get(name='请假流程')
        assert len(flow.steps) == 2
        assert flow.is_active is True

    def test_list_flows(self, member_client):
        """列出审批流程"""
        ApprovalFlow.objects.create(name='报销流程', flow_type='expense', steps=[])
        resp = member_client.get('/api/v1/approvals/flows/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(f['name'] == '报销流程' for f in items)

    def test_update_flow(self, admin_client):
        """更新审批流程"""
        flow = ApprovalFlow.objects.create(name='待更新', flow_type='sensitive', steps=[])
        resp = admin_client.patch(f'/api/v1/approvals/flows/{flow.id}/', {
            'is_active': False,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        flow.refresh_from_db()
        assert flow.is_active is False


@pytest.mark.api
@pytest.mark.django_db
class TestApprovalRequest:
    """审批申请测试"""

    def _make_flow(self):
        return ApprovalFlow.objects.create(
            name='多步流程', flow_type='leave',
            steps=[{'name': '步骤1'}, {'name': '步骤2'}],
        )

    def test_create_request(self, member_client):
        """创建审批申请"""
        flow = self._make_flow()
        resp = member_client.post('/api/v1/approvals/requests/', {
            'flow': flow.id, 'title': '请假1天', 'content': '病假',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        req = ApprovalRequest.objects.get(title='请假1天')
        assert req.applicant == member_client.user
        assert req.status == 'pending'
        assert req.current_step == 0

    def test_approve_advances_step(self, admin_client, make_user):
        """审批通过推进步骤"""
        flow = self._make_flow()
        applicant = make_user(email='app1@test.com')
        req = ApprovalRequest.objects.create(
            applicant=applicant, flow=flow, title='审批推进', content='',
        )
        resp = admin_client.post(f'/api/v1/approvals/requests/{req.id}/approve/', {
            'opinion': '同意',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        req.refresh_from_db()
        assert req.current_step == 1
        assert req.status == 'pending'  # 还未到最后一步

    def test_approve_final_step_approved(self, admin_client, make_user):
        """最后一步审批通过 -> 已通过"""
        flow = self._make_flow()
        applicant = make_user(email='app2@test.com')
        req = ApprovalRequest.objects.create(
            applicant=applicant, flow=flow, title='最终审批', content='', current_step=1,
        )
        resp = admin_client.post(f'/api/v1/approvals/requests/{req.id}/approve/', {
            'opinion': '同意',
        }, format='json')
        assert resp.status_code == 200
        req.refresh_from_db()
        assert req.status == 'approved'

    def test_reject_request(self, admin_client, make_user):
        """驳回申请"""
        flow = self._make_flow()
        applicant = make_user(email='app3@test.com')
        req = ApprovalRequest.objects.create(
            applicant=applicant, flow=flow, title='驳回测试', content='',
        )
        resp = admin_client.post(f'/api/v1/approvals/requests/{req.id}/reject/', {
            'opinion': '理由不充分',
        }, format='json')
        assert resp.status_code == 200
        req.refresh_from_db()
        assert req.status == 'rejected'

    def test_approve_non_pending_rejected(self, admin_client, make_user):
        """非待审批状态不可审批"""
        flow = self._make_flow()
        applicant = make_user(email='app4@test.com')
        req = ApprovalRequest.objects.create(
            applicant=applicant, flow=flow, title='已处理', content='', status='approved',
        )
        resp = admin_client.post(f'/api/v1/approvals/requests/{req.id}/approve/', {}, format='json')
        assert resp.status_code in (400, 409)

    def test_cancel_own_request(self, member_client):
        """申请人取消申请"""
        flow = self._make_flow()
        req = ApprovalRequest.objects.create(
            applicant=member_client.user, flow=flow, title='取消测试', content='',
        )
        resp = member_client.post(f'/api/v1/approvals/requests/{req.id}/cancel/', {}, format='json')
        assert resp.status_code == 200
        req.refresh_from_db()
        assert req.status == 'cancelled'

    def test_cancel_by_non_applicant_forbidden(self, admin_client, make_user):
        """非申请人不可取消"""
        flow = self._make_flow()
        applicant = make_user(email='app5@test.com')
        req = ApprovalRequest.objects.create(
            applicant=applicant, flow=flow, title='他人取消', content='',
        )
        resp = admin_client.post(f'/api/v1/approvals/requests/{req.id}/cancel/', {}, format='json')
        assert resp.status_code in (403, 404)

    def test_my_requests(self, member_client):
        """我的申请"""
        flow = self._make_flow()
        ApprovalRequest.objects.create(
            applicant=member_client.user, flow=flow, title='我的', content='',
        )
        resp = member_client.get('/api/v1/approvals/requests/my_requests/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(r['title'] == '我的' for r in items)

    def test_member_only_sees_own(self, member_client, make_user):
        """普通成员仅看到自己的申请"""
        flow = self._make_flow()
        other = make_user(email='other-approval@test.com')
        ApprovalRequest.objects.create(applicant=other, flow=flow, title='他人的', content='')
        resp = member_client.get('/api/v1/approvals/requests/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        titles = [r['title'] for r in items]
        assert '他人的' not in titles

    def test_review_metadata_recorded(self, admin_client, make_user):
        """审批意见写入 metadata"""
        flow = self._make_flow()
        applicant = make_user(email='app6@test.com')
        req = ApprovalRequest.objects.create(
            applicant=applicant, flow=flow, title='意见记录', content='',
        )
        admin_client.post(f'/api/v1/approvals/requests/{req.id}/approve/', {
            'opinion': '通过意见',
        }, format='json')
        req.refresh_from_db()
        reviews = req.metadata.get('reviews', [])
        assert len(reviews) == 1
        assert reviews[0]['action'] == 'approve'
        assert reviews[0]['opinion'] == '通过意见'
