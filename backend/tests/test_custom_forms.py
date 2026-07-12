"""
N42: 自定义表单测试
- /api/v1/common/forms/             表单 CRUD
- /api/v1/common/form-submissions/  提交记录 CRUD + my_submissions
"""
import pytest

from apps.common.form_models import CustomForm, FormSubmission


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestCustomForm:
    """自定义表单测试"""

    def test_create_form(self, member_client):
        """创建表单"""
        resp = member_client.post('/api/v1/common/forms/', {
            'name': '报名表', 'description': '活动报名',
            'fields': [{'name': 'phone', 'type': 'text'}],
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        form = CustomForm.objects.get(name='报名表')
        assert form.created_by == member_client.user
        assert len(form.fields) == 1

    def test_list_forms(self, member_client):
        """列出表单"""
        CustomForm.objects.create(name='列表表', fields=[])
        resp = member_client.get('/api/v1/common/forms/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(f['name'] == '列表表' for f in items)

    def test_retrieve_form(self, member_client):
        """查看表单详情"""
        form = CustomForm.objects.create(name='详情表', fields=[{'a': 1}])
        resp = member_client.get(f'/api/v1/common/forms/{form.id}/')
        assert resp.status_code == 200
        assert extract_data(resp)['name'] == '详情表'

    def test_update_form(self, member_client):
        """更新表单"""
        form = CustomForm.objects.create(name='待更新', fields=[])
        resp = member_client.patch(f'/api/v1/common/forms/{form.id}/', {
            'is_active': False,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        form.refresh_from_db()
        assert form.is_active is False

    def test_delete_form(self, member_client):
        """删除表单"""
        form = CustomForm.objects.create(name='待删除', fields=[])
        resp = member_client.delete(f'/api/v1/common/forms/{form.id}/')
        assert resp.status_code in (200, 204)
        assert not CustomForm.objects.filter(id=form.id).exists()


@pytest.mark.api
@pytest.mark.django_db
class TestFormSubmission:
    """表单提交测试"""

    def test_submit_form(self, member_client):
        """提交表单"""
        form = CustomForm.objects.create(name='提交表', fields=[])
        resp = member_client.post('/api/v1/common/form-submissions/', {
            'form': form.id, 'data': {'phone': '13800000000'},
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        sub = FormSubmission.objects.get(form=form)
        assert sub.user == member_client.user
        assert sub.data['phone'] == '13800000000'

    def test_my_submissions(self, member_client):
        """我的提交"""
        form = CustomForm.objects.create(name='我的提交表', fields=[])
        FormSubmission.objects.create(form=form, user=member_client.user, data={'a': 1})
        resp = member_client.get('/api/v1/common/form-submissions/my_submissions/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_member_only_sees_own_submissions(self, member_client, make_user):
        """普通成员仅看到自己的提交"""
        form = CustomForm.objects.create(name='隔离表', fields=[])
        other = make_user(email='other-sub@test.com')
        FormSubmission.objects.create(form=form, user=other, data={})
        resp = member_client.get('/api/v1/common/form-submissions/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert all(s.get('user') != other.id for s in items)

    def test_list_submissions_admin_sees_all(self, admin_client, make_user):
        """管理员看到所有提交"""
        form = CustomForm.objects.create(name='管理员表', fields=[])
        u = make_user(email='sub-user@test.com')
        FormSubmission.objects.create(form=form, user=u, data={'k': 'v'})
        resp = admin_client.get('/api/v1/common/form-submissions/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(s.get('user') == u.id for s in items)

    def test_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.get('/api/v1/common/forms/')
        assert resp.status_code in (401, 403)
