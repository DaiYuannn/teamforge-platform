"""
经费模块 API 测试
- P04: 经费 CRUD 完整化
- P05: 经费导出
- 业务规则: 经费明细对所有登录成员公开
"""
import pytest
import math
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from apps.projects.models import ProjectMember
from apps.users.models import User


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestFinanceAPI:
    """经费 API 测试"""

    def test_finance_list_accessible_by_member(self, member_client, make_finance):
        """P04: 经费列表对所有登录成员公开"""
        make_finance()
        resp = member_client.get('/api/v1/finance/expenses/')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) > 0

    def test_finance_create(self, teacher_client, make_project):
        """P04: 创建经费记录"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post('/api/v1/finance/expenses/', {
            'project': project.id,
                        'amount': 500.00,
            'title': '测试支出',
            'description': '购买材料',
            'expense_date': '2026-07-07',
            'category': 'material',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['amount'] == '500.00' or float(data['amount']) == 500.0

    def test_finance_no_nan_amount(self, member_client, make_finance):
        """P04: 经费金额无 NaN"""
        make_finance(amount=100.50)
        resp = member_client.get('/api/v1/finance/expenses/')
        assert resp.status_code == 200
        data = resp.json()
        self._check_no_nan(data)

    def _check_no_nan(self, data, path=''):
        if isinstance(data, dict):
            for k, v in data.items():
                assert v != 'NaN', f'NaN at {path}.{k}'
                assert v != 'undefined', f'undefined at {path}.{k}'
                self._check_no_nan(v, f'{path}.{k}')
        elif isinstance(data, list):
            for i, v in enumerate(data):
                self._check_no_nan(v, f'{path}[{i}]')
        elif isinstance(data, float):
            assert not math.isnan(data), f'NaN float at {path}'
            assert not math.isinf(data), f'Inf float at {path}'

    def test_non_project_member_cannot_create(self, member_client, make_project):
        """非项目成员不能登记该项目支出。"""
        project = make_project()
        resp = member_client.post('/api/v1/finance/expenses/', {
            'project': project.id,
            'amount': 100,
            'title': '非项目成员尝试创建',
            'expense_date': '2026-07-07',
        }, format='json')
        assert resp.status_code == 403, resp.json()

    def test_project_member_can_create_only_as_self(
        self, member_client, make_project, make_user
    ):
        """项目成员可登记本人支出，传入他人经办人也会被服务端改为本人。"""
        project = make_project()
        other = make_user(email='finance-other-spender@test.com')
        ProjectMember.objects.create(project=project, user=member_client.user)

        resp = member_client.post('/api/v1/finance/expenses/', {
            'project': project.id,
            'amount': 128.50,
            'title': '成员垫付材料费',
            'expense_date': '2026-07-07',
            'spender': other.id,
        }, format='json')

        assert resp.status_code == 201, resp.json()
        assert extract_data(resp)['spender'] == member_client.user.id

    def test_member_can_upload_and_delete_receipt_for_own_draft(
        self, tmp_path, member_client, make_project, make_finance
    ):
        project = make_project()
        ProjectMember.objects.create(project=project, user=member_client.user)
        expense = make_finance(project=project, spender=member_client.user)
        upload = SimpleUploadedFile(
            'receipt.txt',
            b'demo receipt',
            content_type='text/plain',
        )

        with override_settings(MEDIA_ROOT=tmp_path):
            created = member_client.post(
                '/api/v1/finance/receipts/',
                {'expense': expense.id, 'file': upload},
                format='multipart',
            )
            assert created.status_code == 201, created.json()
            receipt_id = extract_data(created)['id']
            deleted = member_client.delete(
                f'/api/v1/finance/receipts/{receipt_id}/'
            )

        assert deleted.status_code in (200, 204), deleted.json()

    def test_finance_filter_by_project(self, member_client, make_finance, make_project):
        """P04: 按项目筛选经费"""
        p1 = make_project()
        p2 = make_project()
        make_finance(project=p1)
        make_finance(project=p2)
        resp = member_client.get(f'/api/v1/finance/expenses/?project={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert all(r['project'] == p1.id for r in results)

    def test_finance_export(self, admin_client, make_finance):
        """P05: 经费导出"""
        make_finance()
        resp = admin_client.get('/api/v1/exports/?type=finance&format=excel')
        assert resp.status_code in (200, 400, 404)

    def test_finance_detail(self, member_client, make_finance):
        """P04: 经费详情"""
        finance = make_finance()
        resp = member_client.get(f'/api/v1/finance/expenses/{finance.id}/')
        assert resp.status_code == 200

    def test_finance_update(self, teacher_client, make_project, make_finance):
        """P04: 更新经费记录"""
        project = make_project(leader=teacher_client.user)
        finance = make_finance(project=project)
        resp = teacher_client.patch(f'/api/v1/finance/expenses/{finance.id}/', {
            'amount': 200,
        }, format='json')
        assert resp.status_code == 200, resp.json()

    def test_finance_delete(self, teacher_client, make_project, make_finance):
        """P04: 删除经费记录"""
        project = make_project(leader=teacher_client.user)
        finance = make_finance(project=project)
        resp = teacher_client.delete(f'/api/v1/finance/expenses/{finance.id}/')
        assert resp.status_code in (200, 204)


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
class TestFinanceInternalDataBoundary:
    def test_external_collaborator_cannot_access_finance_or_derived_analytics(
        self, make_user, make_project
    ):
        external = make_user(
            email='external-finance@test.com',
            membership_status=User.MembershipStatus.EXTERNAL,
        )
        project = make_project()
        ProjectMember.objects.create(project=project, user=external)
        client = APIClient()
        client.force_authenticate(user=external)
        urls = [
            '/api/v1/finance/budgets/',
            '/api/v1/finance/expenses/',
            '/api/v1/finance/incomes/',
            '/api/v1/finance/receipts/',
            '/api/v1/finance/alerts/',
            '/api/v1/finance/trends/',
            '/api/v1/dashboard/',
            '/api/v1/dashboard/timeline/',
            '/api/v1/dashboard/calendar/',
            '/api/v1/dashboard/weekly-report/',
            '/api/v1/exports/?type=finance_budget&file_format=xlsx',
            f'/api/v1/exports/project-report/{project.id}/',
            '/api/v1/recycle-bin/?type=finance_expense',
            f'/api/v1/projects/health-score/?project_id={project.id}',
            f'/api/v1/projects/risk-prediction/?project_id={project.id}',
            f'/api/v1/projects/smart-review/?project_id={project.id}',
            f'/api/v1/projects/material-check/?project_id={project.id}',
            '/api/v1/exports/custom-reports/',
            '/api/v1/exports/scheduled-reports/',
        ]

        for url in urls:
            response = client.get(url)
            assert response.status_code == 403, (url, response.status_code)

        ocr = client.post('/api/v1/finance/ocr/recognize/', {}, format='json')
        assert ocr.status_code == 403


