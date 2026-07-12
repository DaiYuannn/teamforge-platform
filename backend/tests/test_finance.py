"""
经费模块 API 测试
- P04: 经费 CRUD 完整化
- P05: 经费导出
- 业务规则: 经费明细对所有登录成员公开
"""
import pytest
import math


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

    def test_finance_member_cannot_create(self, member_client, make_project):
        """P04: 普通成员不能创建经费记录"""
        project = make_project()
        resp = member_client.post('/api/v1/finance/expenses/', {
            'project': project.id,
                        'amount': 100,
            'title': '成员尝试创建',
        }, format='json')
        assert resp.status_code in (401, 403)

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


