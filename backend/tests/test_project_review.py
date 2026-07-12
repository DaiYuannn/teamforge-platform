"""
项目复盘模块 API 测试
- 创建复盘（仅老师/管理员）
- 列表 / 详情 / 更新
- 提交复盘 / 审阅完成
- 普通成员不可创建
- OneToOne：每个项目仅一条复盘
"""
import pytest

from apps.projects.review_models import ProjectReview


REVIEW_URL = '/api/v1/projects/reviews/'


def extract_data(response):
    """从统一响应结构中提取 data 字段"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestProjectReviewAPI:
    """项目复盘 API 测试"""

    # ---------- 创建 ----------

    def test_review_create_by_teacher(self, teacher_client, make_project):
        """老师可以创建项目复盘"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post(REVIEW_URL, {
            'project': project.id,
            'summary': '项目整体顺利',
            'achievements': '完成全部功能',
            'overall_score': 4,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['project'] == project.id
        assert data['status'] == ProjectReview.Status.DRAFT
        assert data['overall_score'] == 4
        assert data['summary'] == '项目整体顺利'

    def test_review_create_by_admin(self, admin_client, make_project):
        """管理员可以创建项目复盘"""
        project = make_project()
        resp = admin_client.post(REVIEW_URL, {
            'project': project.id,
            'summary': '管理员创建的复盘',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['project'] == project.id

    def test_review_member_cannot_create(self, member_client, make_project):
        """普通成员不能创建项目复盘"""
        project = make_project()
        resp = member_client.post(REVIEW_URL, {
            'project': project.id,
            'summary': '成员尝试创建',
        }, format='json')
        assert resp.status_code in (401, 403), resp.json()

    def test_review_one_per_project(self, teacher_client, make_project):
        """OneToOne：同一项目仅能创建一条复盘"""
        project = make_project(leader=teacher_client.user)
        # 第一次创建成功
        resp1 = teacher_client.post(REVIEW_URL, {
            'project': project.id,
            'summary': '第一条复盘',
        }, format='json')
        assert resp1.status_code in (200, 201)

        # 第二次创建应被拒绝（业务层友好提示）
        resp2 = teacher_client.post(REVIEW_URL, {
            'project': project.id,
            'summary': '第二条复盘',
        }, format='json')
        assert resp2.status_code in (400, 500), resp2.json()

    # ---------- 列表 / 详情 ----------

    def test_review_list(self, member_client, make_project):
        """所有登录成员可查看复盘列表"""
        project = make_project()
        ProjectReview.objects.create(project=project, summary='复盘A')
        resp = member_client.get(REVIEW_URL)
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) >= 1

    def test_review_detail(self, member_client, make_project):
        """复盘详情"""
        project = make_project()
        review = ProjectReview.objects.create(project=project, summary='详情测试')
        resp = member_client.get(f'{REVIEW_URL}{review.id}/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['id'] == review.id
        assert data['project_name'] == project.name

    # ---------- 更新 ----------

    def test_review_update_by_teacher(self, teacher_client, make_project):
        """老师可更新复盘"""
        project = make_project(leader=teacher_client.user)
        review = ProjectReview.objects.create(project=project, summary='初始')
        resp = teacher_client.patch(f'{REVIEW_URL}{review.id}/', {
            'summary': '更新后的总结',
            'overall_score': 5,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['summary'] == '更新后的总结'
        assert data['overall_score'] == 5

    def test_review_member_cannot_update(self, member_client, make_project):
        """普通成员不能更新复盘"""
        project = make_project()
        review = ProjectReview.objects.create(project=project, summary='初始')
        resp = member_client.patch(f'{REVIEW_URL}{review.id}/', {
            'summary': '成员尝试更新',
        }, format='json')
        assert resp.status_code in (401, 403), resp.json()

    # ---------- 提交 ----------

    def test_review_submit(self, teacher_client, make_project):
        """提交复盘：状态推进为 submitted，记录复盘人/日期"""
        project = make_project(leader=teacher_client.user)
        review = ProjectReview.objects.create(project=project, summary='待提交')
        assert review.status == ProjectReview.Status.DRAFT

        resp = teacher_client.post(f'{REVIEW_URL}{review.id}/submit/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == ProjectReview.Status.SUBMITTED
        assert data['reviewer'] == teacher_client.user.id
        assert data['review_date'] is not None

    def test_review_submit_member_forbidden(self, member_client, make_project):
        """普通成员不能提交复盘"""
        project = make_project()
        review = ProjectReview.objects.create(project=project, summary='待提交')
        resp = member_client.post(f'{REVIEW_URL}{review.id}/submit/')
        assert resp.status_code in (401, 403), resp.json()

    # ---------- 审阅 ----------

    def test_review_approve(self, teacher_client, make_project):
        """审阅完成：状态推进为 reviewed"""
        project = make_project(leader=teacher_client.user)
        review = ProjectReview.objects.create(
            project=project,
            summary='已提交',
            status=ProjectReview.Status.SUBMITTED,
        )
        resp = teacher_client.post(f'{REVIEW_URL}{review.id}/approve/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == ProjectReview.Status.REVIEWED

    def test_review_approve_admin(self, admin_client, make_project):
        """管理员可审阅复盘"""
        project = make_project()
        review = ProjectReview.objects.create(
            project=project,
            status=ProjectReview.Status.SUBMITTED,
        )
        resp = admin_client.post(f'{REVIEW_URL}{review.id}/approve/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == ProjectReview.Status.REVIEWED

    # ---------- 评分校验 ----------

    def test_review_invalid_score(self, teacher_client, make_project):
        """评分超出 1-5 范围应被拒绝"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post(REVIEW_URL, {
            'project': project.id,
            'overall_score': 6,
        }, format='json')
        assert resp.status_code == 400, resp.json()

    # ---------- 删除 ----------

    def test_review_delete_by_teacher(self, teacher_client, make_project):
        """老师可删除复盘"""
        project = make_project(leader=teacher_client.user)
        review = ProjectReview.objects.create(project=project, summary='待删除')
        resp = teacher_client.delete(f'{REVIEW_URL}{review.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not ProjectReview.objects.filter(id=review.id).exists()


@pytest.mark.model
@pytest.mark.django_db
class TestProjectReviewModel:
    """项目复盘模型测试"""

    def test_review_default_status(self, make_project):
        """默认状态为 draft"""
        project = make_project()
        review = ProjectReview.objects.create(project=project)
        assert review.status == ProjectReview.Status.DRAFT

    def test_review_str(self, make_project):
        """__str__ 包含项目名与状态"""
        project = make_project(name='测试项目X')
        review = ProjectReview.objects.create(project=project)
        assert '测试项目X' in str(review)
        assert '草稿' in str(review)

    def test_review_one_to_one(self, make_project):
        """OneToOne：同一项目第二次创建会抛出异常"""
        project = make_project()
        ProjectReview.objects.create(project=project, summary='第一条')
        with pytest.raises(Exception):
            ProjectReview.objects.create(project=project, summary='第二条')

    def test_review_related_name(self, make_project):
        """反向关系 project.review 可访问"""
        project = make_project()
        review = ProjectReview.objects.create(project=project, summary='反向关系')
        assert project.review == review
