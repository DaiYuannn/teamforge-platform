"""
敏感资料 API 测试
- P03: 敏感文件与审批连通
- 业务规则: 申请、审批、限时查看/下载、日志记录
- 契约: sensitive_data/usage_scenario/is_download/action/approval_opinion/expire_hours
"""
import pytest
from django.utils import timezone

from apps.audit.models import OperationLog


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestSensitiveDataAPI:
    """敏感资料 API 测试"""

    def test_sensitive_list_member(self, member_client, make_sensitive_data):
        """普通成员可以查看敏感资料列表"""
        make_sensitive_data()
        resp = member_client.get('/api/v1/sensitive/data/')
        assert resp.status_code == 200

    def test_sensitive_data_encrypted(self, make_sensitive_data):
        """敏感数据内容必须加密存储"""
        sd = make_sensitive_data()
        assert sd.encrypted_content != '测试敏感明文内容'
        assert len(sd.encrypted_content) > 0

    def test_sensitive_request_create(self, member_client, make_sensitive_data):
        """P03: 创建敏感资料访问申请"""
        sd = make_sensitive_data()
        resp = member_client.post('/api/v1/sensitive/requests/', {
            'sensitive_data': sd.id,
            'usage_scenario': '项目需要查看身份证号',
            'is_download': False,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['usage_scenario'] == '项目需要查看身份证号'
        assert data['is_download'] == False

    def test_sensitive_request_approve(self, approver_client, make_sensitive_data, make_user):
        """P03: 审批敏感资料申请"""
        from apps.sensitive.models import SensitiveAccessRequest
        sd = make_sensitive_data()
        applicant = make_user(email='applicant1@test.com')
        req = SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            usage_scenario='测试审批',
            is_download=False,
            status='pending',
        )
        resp = approver_client.post(f'/api/v1/sensitive/requests/{req.id}/approve/', {
            'action': 'approve',
            'approval_opinion': '同意',
            'expire_hours': 24,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        req.refresh_from_db()
        assert req.status == 'approved'
        assert req.approval_opinion == '同意'

    def test_sensitive_request_reject(self, approver_client, make_sensitive_data, make_user):
        """P03: 驳回敏感资料申请"""
        from apps.sensitive.models import SensitiveAccessRequest
        sd = make_sensitive_data()
        applicant = make_user(email='applicant2@test.com')
        req = SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            usage_scenario='测试驳回',
            is_download=True,
            status='pending',
        )
        resp = approver_client.post(f'/api/v1/sensitive/requests/{req.id}/reject/', {
            'action': 'reject',
            'approval_opinion': '不需要下载',
            'expire_hours': 0,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        req.refresh_from_db()
        assert req.status == 'rejected'

    def test_processed_request_cannot_be_reviewed_twice(
        self,
        approver_client,
        make_sensitive_data,
        make_user,
    ):
        from apps.sensitive.models import SensitiveAccessRequest

        req = SensitiveAccessRequest.objects.create(
            sensitive_data=make_sensitive_data(),
            applicant=make_user(email='single-review-applicant@test.com'),
            usage_scenario='不可重复审批',
            status=SensitiveAccessRequest.Status.PENDING,
        )

        approved = approver_client.post(
            f'/api/v1/sensitive/requests/{req.id}/approve/',
            {'action': 'approve', 'expire_hours': 1},
            format='json',
        )
        rejected = approver_client.post(
            f'/api/v1/sensitive/requests/{req.id}/reject/',
            {'action': 'reject', 'expire_hours': 0},
            format='json',
        )

        assert approved.status_code == 200
        assert rejected.status_code == 400
        req.refresh_from_db()
        assert req.status == SensitiveAccessRequest.Status.APPROVED
        assert OperationLog.objects.filter(
            module='sensitive',
            object_type='SensitiveAccessRequest',
            object_id=str(req.id),
        ).count() == 1

    def test_sensitive_member_cannot_approve(self, member_client, make_sensitive_data, make_user):
        """P03: 普通成员不能审批"""
        from apps.sensitive.models import SensitiveAccessRequest
        sd = make_sensitive_data()
        applicant = make_user(email='applicant3@test.com')
        req = SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            usage_scenario='测试',
            is_download=False,
            status='pending',
        )
        resp = member_client.post(f'/api/v1/sensitive/requests/{req.id}/approve/', {
            'action': 'approve',
            'approval_opinion': '越权',
            'expire_hours': 24,
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_access_request_cannot_be_rewritten_with_generic_patch(
        self,
        member_client,
        make_sensitive_data,
    ):
        from apps.sensitive.models import SensitiveAccessRequest

        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=make_sensitive_data(),
            applicant=member_client.user,
            usage_scenario='等待独立审批',
            is_download=False,
            status=SensitiveAccessRequest.Status.PENDING,
        )

        response = member_client.patch(
            f'/api/v1/sensitive/requests/{request_obj.id}/',
            {
                'status': SensitiveAccessRequest.Status.APPROVED,
                'approver': member_client.user.id,
                'access_expires_at': '2099-01-01T00:00:00Z',
                'is_download': True,
            },
            format='json',
        )

        assert response.status_code == 405
        request_obj.refresh_from_db()
        assert request_obj.status == SensitiveAccessRequest.Status.PENDING
        assert request_obj.approver_id is None
        assert request_obj.access_expires_at is None
        assert request_obj.is_download is False

    def test_approver_cannot_approve_their_own_request(
        self,
        approver_client,
        make_sensitive_data,
    ):
        from apps.sensitive.models import SensitiveAccessRequest

        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=make_sensitive_data(),
            applicant=approver_client.user,
            usage_scenario='审批角色也必须由他人审批',
            is_download=True,
            status=SensitiveAccessRequest.Status.PENDING,
        )

        response = approver_client.post(
            f'/api/v1/sensitive/requests/{request_obj.id}/approve/',
            {
                'action': 'approve',
                'approval_opinion': '自行放行',
                'expire_hours': 24,
            },
            format='json',
        )

        assert response.status_code == 400
        request_obj.refresh_from_db()
        assert request_obj.status == SensitiveAccessRequest.Status.PENDING
        assert request_obj.approver_id is None

    @pytest.mark.parametrize('role', ['sens_approver', 'teacher', 'sys_admin'])
    def test_pending_approve_roles_share_queue_but_exclude_own_requests(
        self,
        role,
        api_client,
        make_sensitive_data,
        make_user,
    ):
        from apps.sensitive.models import SensitiveAccessRequest

        reviewer = make_user(
            email=f'pending-{role}@test.com',
            global_role=role,
        )
        applicant = make_user(email=f'pending-applicant-{role}@test.com')
        sensitive = make_sensitive_data()
        own_request = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=reviewer,
            reason='审批角色本人申请',
            status=SensitiveAccessRequest.Status.PENDING,
        )
        shared_request = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=applicant,
            reason='进入共享审批队列',
            status=SensitiveAccessRequest.Status.PENDING,
        )
        processed_request = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=applicant,
            reason='已经处理',
            status=SensitiveAccessRequest.Status.APPROVED,
        )
        api_client.force_authenticate(user=reviewer)

        response = api_client.get(
            '/api/v1/sensitive/requests/pending_approve/'
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        returned_ids = {item['id'] for item in data['results']}
        assert shared_request.id in returned_ids
        assert own_request.id not in returned_ids
        assert processed_request.id not in returned_ids

        my_response = api_client.get(
            '/api/v1/sensitive/requests/my_requests/'
        )
        assert my_response.status_code == 200, my_response.json()
        my_ids = {
            item['id'] for item in extract_data(my_response)['results']
        }
        assert own_request.id in my_ids

    def test_member_cannot_access_pending_approve(
        self,
        member_client,
    ):
        response = member_client.get(
            '/api/v1/sensitive/requests/pending_approve/'
        )

        assert response.status_code == 403

    def test_my_requests_uses_standard_page_and_page_size_contract(
        self,
        member_client,
        make_sensitive_data,
        make_user,
    ):
        from apps.sensitive.models import SensitiveAccessRequest

        sensitive = make_sensitive_data()
        other_user = make_user(email='other-sensitive-applicant@test.com')
        own_requests = [
            SensitiveAccessRequest.objects.create(
                sensitive_data=sensitive,
                applicant=member_client.user,
                reason=f'本人申请 {index}',
            )
            for index in range(5)
        ]
        SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=other_user,
            reason='其他成员申请',
        )

        response = member_client.get(
            '/api/v1/sensitive/requests/my_requests/',
            {'page': 2, 'page_size': 2},
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert 'page_size' in data
        assert data['count'] == len(own_requests)
        assert data['current_page'] == 2
        assert data['total_pages'] == 3
        assert len(data['results']) == 2
        assert data['next'] is not None
        assert data['previous'] is not None
        assert {
            item['applicant'] for item in data['results']
        } == {member_client.user.id}

    def test_pending_approve_uses_standard_page_and_page_size_contract(
        self,
        approver_client,
        make_sensitive_data,
        make_user,
    ):
        from apps.sensitive.models import SensitiveAccessRequest

        sensitive = make_sensitive_data()
        applicant = make_user(email='paginated-pending-applicant@test.com')
        pending_requests = [
            SensitiveAccessRequest.objects.create(
                sensitive_data=sensitive,
                applicant=applicant,
                reason=f'待审批申请 {index}',
            )
            for index in range(5)
        ]
        own_request = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=approver_client.user,
            reason='不应进入本人审批队列',
        )

        response = approver_client.get(
            '/api/v1/sensitive/requests/pending_approve/',
            {'page': 2, 'page_size': 2},
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert 'page_size' in data
        assert data['count'] == len(pending_requests)
        assert data['current_page'] == 2
        assert data['total_pages'] == 3
        assert len(data['results']) == 2
        assert data['next'] is not None
        assert data['previous'] is not None
        assert own_request.id not in {
            item['id'] for item in data['results']
        }

    def test_sensitive_access_logged(self, approver_client, make_sensitive_data, make_user):
        """P03: 敏感资料访问必须记录日志"""
        from apps.sensitive.models import SensitiveAccessRequest
        from apps.audit.models import OperationLog
        sd = make_sensitive_data()
        applicant = make_user(email='applicant4@test.com')
        req = SensitiveAccessRequest.objects.create(
            sensitive_data=sd,
            applicant=applicant,
            usage_scenario='测试日志',
            is_download=False,
            status='pending',
        )
        approver_client.post(f'/api/v1/sensitive/requests/{req.id}/approve/', {
            'action': 'approve',
            'approval_opinion': '同意',
            'expire_hours': 24,
        }, format='json')
        logs = OperationLog.objects.filter(module='sensitive')
        assert logs.exists(), '敏感资料审批必须记录操作日志'
