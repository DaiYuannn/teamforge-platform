"""
N26: 动态流（Activity Feed）测试
- 模型层：Activity 创建、类型枚举
- 服务层：log_activity 函数
- API 层：全局动态流、项目动态流（分页、过滤）
- 权限验证
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def get_results(response):
    """从分页或非分页响应中提取结果列表"""
    data = extract_data(response)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return data


@pytest.mark.model
@pytest.mark.django_db
class TestActivityModel:
    """动态流模型测试"""

    def test_create_activity(self, make_user, make_project):
        """创建动态"""
        from apps.common.activity_models import Activity
        user = make_user()
        project = make_project()
        activity = Activity.objects.create(
            activity_type=Activity.Type.PROJECT_CREATED,
            actor=user,
            project=project,
            target_type='project',
            target_id=project.id,
            description='创建了项目',
            metadata={'name': project.name},
        )
        assert activity.id is not None
        assert activity.activity_type == 'project_created'
        assert activity.actor == user
        assert activity.project == project
        assert activity.target_type == 'project'
        assert activity.target_id == project.id
        assert activity.description == '创建了项目'
        assert activity.metadata == {'name': project.name}

    def test_activity_types(self):
        """动态类型枚举完整"""
        from apps.common.activity_models import Activity
        types = [t[0] for t in Activity.Type.choices]
        assert 'project_created' in types
        assert 'project_updated' in types
        assert 'project_closed' in types
        assert 'task_created' in types
        assert 'task_completed' in types
        assert 'task_updated' in types
        assert 'file_uploaded' in types
        assert 'comment_created' in types
        assert 'member_joined' in types
        assert 'member_left' in types

    def test_activity_default_fields(self):
        """默认字段值"""
        from apps.common.activity_models import Activity
        activity = Activity.objects.create(
            activity_type=Activity.Type.TASK_CREATED,
        )
        assert activity.actor is None
        assert activity.project is None
        assert activity.target_type == ''
        assert activity.target_id is None
        assert activity.description == ''
        assert activity.metadata == {}

    def test_activity_ordering(self, make_user):
        """动态按创建时间倒序"""
        from apps.common.activity_models import Activity
        user = make_user()
        a1 = Activity.objects.create(activity_type=Activity.Type.PROJECT_CREATED, actor=user)
        a2 = Activity.objects.create(activity_type=Activity.Type.TASK_CREATED, actor=user)
        activities = list(Activity.objects.all())
        # 最新的在前
        assert activities[0].id == a2.id
        assert activities[1].id == a1.id

    def test_activity_str(self, make_user):
        """__str__ 方法"""
        from apps.common.activity_models import Activity
        activity = Activity.objects.create(
            activity_type=Activity.Type.PROJECT_CREATED,
            description='测试描述',
        )
        assert '创建项目' in str(activity)
        assert '测试描述' in str(activity)


@pytest.mark.model
@pytest.mark.django_db
class TestLogActivityService:
    """log_activity 服务函数测试"""

    def test_log_activity_basic(self, make_user, make_project):
        """基本调用"""
        from apps.common.activity_services import log_activity
        from apps.common.activity_models import Activity
        user = make_user()
        project = make_project()
        activity = log_activity(
            activity_type=Activity.Type.PROJECT_CREATED,
            actor=user,
            project=project,
            target_type='project',
            target_id=project.id,
            description='创建了项目',
            metadata={'name': project.name},
        )
        assert activity.id is not None
        assert Activity.objects.count() == 1
        assert activity.actor == user

    def test_log_activity_minimal(self):
        """最小参数调用"""
        from apps.common.activity_services import log_activity
        from apps.common.activity_models import Activity
        activity = log_activity(activity_type=Activity.Type.FILE_UPLOADED)
        assert activity.id is not None
        assert activity.actor is None
        assert activity.project is None
        assert activity.metadata == {}

    def test_log_activity_metadata_none(self, make_user):
        """metadata=None 时默认空 dict"""
        from apps.common.activity_services import log_activity
        from apps.common.activity_models import Activity
        user = make_user()
        activity = log_activity(
            activity_type=Activity.Type.TASK_COMPLETED,
            actor=user,
            metadata=None,
        )
        assert activity.metadata == {}

    def test_log_activity_multiple(self, make_user, make_project):
        """记录多条动态"""
        from apps.common.activity_services import log_activity
        from apps.common.activity_models import Activity
        user = make_user()
        project = make_project()
        log_activity(Activity.Type.PROJECT_CREATED, actor=user, project=project)
        log_activity(Activity.Type.TASK_CREATED, actor=user, project=project)
        log_activity(Activity.Type.FILE_UPLOADED, actor=user, project=project)
        assert Activity.objects.count() == 3
        assert Activity.objects.filter(project=project).count() == 3


@pytest.mark.api
@pytest.mark.django_db
class TestActivityFeedAPI:
    """全局动态流 API 测试"""

    def test_feed_empty(self, member_client):
        """空动态流"""
        resp = member_client.get('/api/v1/activities/')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 0

    def test_feed_with_data(self, member_client, make_user, make_project):
        """有数据的动态流"""
        from apps.common.activity_services import log_activity
        user = make_user()
        project = make_project()
        log_activity('project_created', actor=user, project=project, description='创建项目A')
        log_activity('task_created', actor=user, project=project, description='创建任务')

        resp = member_client.get('/api/v1/activities/')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 2

    def test_feed_includes_fields(self, member_client, make_user, make_project):
        """动态流包含必要字段"""
        from apps.common.activity_services import log_activity
        user = make_user()
        project = make_project()
        log_activity(
            'project_created', actor=user, project=project,
            description='字段测试', metadata={'key': 'value'},
        )
        resp = member_client.get('/api/v1/activities/')
        results = get_results(resp)
        assert len(results) == 1
        item = results[0]
        assert item['activity_type'] == 'project_created'
        assert item['type_display'] == '创建项目'
        assert item['actor_name'] == user.name
        assert item['project_name'] == project.name
        assert item['description'] == '字段测试'
        assert item['metadata'] == {'key': 'value'}
        assert 'created_at' in item

    def test_filter_by_project(self, member_client, make_user, make_project):
        """按项目过滤"""
        from apps.common.activity_services import log_activity
        user = make_user()
        p1 = make_project()
        p2 = make_project()
        log_activity('project_created', actor=user, project=p1, description='项目1动态')
        log_activity('project_created', actor=user, project=p2, description='项目2动态')

        resp = member_client.get(f'/api/v1/activities/?project={p1.id}')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 1
        assert results[0]['description'] == '项目1动态'

    def test_filter_by_type(self, member_client, make_user, make_project):
        """按动态类型过滤"""
        from apps.common.activity_services import log_activity
        user = make_user()
        project = make_project()
        log_activity('project_created', actor=user, project=project)
        log_activity('task_created', actor=user, project=project)
        log_activity('task_completed', actor=user, project=project)

        resp = member_client.get('/api/v1/activities/?type=task_created')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 1
        assert results[0]['activity_type'] == 'task_created'

    def test_filter_by_actor(self, member_client, make_user, make_project):
        """按操作人过滤"""
        from apps.common.activity_services import log_activity
        u1 = make_user(email='actor1@test.com')
        u2 = make_user(email='actor2@test.com')
        project = make_project()
        log_activity('project_created', actor=u1, project=project)
        log_activity('task_created', actor=u2, project=project)

        resp = member_client.get(f'/api/v1/activities/?actor={u1.id}')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 1
        assert results[0]['actor'] == u1.id

    def test_filter_combined(self, member_client, make_user, make_project):
        """组合过滤"""
        from apps.common.activity_services import log_activity
        u1 = make_user(email='combo1@test.com')
        u2 = make_user(email='combo2@test.com')
        p1 = make_project()
        log_activity('project_created', actor=u1, project=p1)
        log_activity('task_created', actor=u2, project=p1)
        log_activity('task_created', actor=u1, project=p1)

        resp = member_client.get(f'/api/v1/activities/?project={p1.id}&type=task_created&actor={u1.id}')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 1
        assert results[0]['activity_type'] == 'task_created'
        assert results[0]['actor'] == u1.id

    def test_feed_pagination(self, member_client, make_user, make_project):
        """分页"""
        from apps.common.activity_services import log_activity
        user = make_user()
        project = make_project()
        for i in range(25):
            log_activity('task_created', actor=user, project=project, description=f'任务{i}')

        resp = member_client.get('/api/v1/activities/?page_size=10&page=1')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 分页结构
        assert data['count'] == 25
        assert len(data['results']) == 10

        resp2 = member_client.get('/api/v1/activities/?page_size=10&page=3')
        data2 = extract_data(resp2)
        assert len(data2['results']) == 5

    def test_feed_ordering(self, member_client, make_user, make_project):
        """动态按时间倒序（最新在前）"""
        from apps.common.activity_services import log_activity
        import time
        user = make_user()
        project = make_project()
        log_activity('project_created', actor=user, project=project, description='第一条')
        log_activity('task_created', actor=user, project=project, description='第二条')

        resp = member_client.get('/api/v1/activities/')
        results = get_results(resp)
        # 第二条（最新）在前
        assert results[0]['description'] == '第二条'
        assert results[1]['description'] == '第一条'

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证不能访问"""
        resp = api_client.get('/api/v1/activities/')
        assert resp.status_code == 401


@pytest.mark.api
@pytest.mark.django_db
class TestProjectActivityAPI:
    """项目动态流 API 测试"""

    def test_project_activity(self, member_client, make_user, make_project):
        """项目动态流"""
        from apps.common.activity_services import log_activity
        user = make_user()
        p1 = make_project()
        p2 = make_project()
        log_activity('project_created', actor=user, project=p1, description='项目1创建')
        log_activity('task_created', actor=user, project=p1, description='项目1任务')
        log_activity('project_created', actor=user, project=p2, description='项目2创建')

        resp = member_client.get(f'/api/v1/activities/project/{p1.id}/')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 2
        descs = [r['description'] for r in results]
        assert '项目1创建' in descs
        assert '项目1任务' in descs
        assert '项目2创建' not in descs

    def test_project_activity_empty(self, member_client, make_project):
        """项目无动态"""
        project = make_project()
        resp = member_client.get(f'/api/v1/activities/project/{project.id}/')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 0

    def test_project_activity_not_found(self, member_client):
        """项目不存在"""
        resp = member_client.get('/api/v1/activities/project/999999/')
        assert resp.status_code == 404

    def test_project_activity_filter_type(self, member_client, make_user, make_project):
        """项目动态流按类型过滤"""
        from apps.common.activity_services import log_activity
        user = make_user()
        project = make_project()
        log_activity('project_created', actor=user, project=project)
        log_activity('task_created', actor=user, project=project)
        log_activity('task_completed', actor=user, project=project)

        resp = member_client.get(f'/api/v1/activities/project/{project.id}/?type=task_completed')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 1
        assert results[0]['activity_type'] == 'task_completed'

    def test_project_activity_filter_actor(self, member_client, make_user, make_project):
        """项目动态流按操作人过滤"""
        from apps.common.activity_services import log_activity
        u1 = make_user(email='pa1@test.com')
        u2 = make_user(email='pa2@test.com')
        project = make_project()
        log_activity('project_created', actor=u1, project=project)
        log_activity('task_created', actor=u2, project=project)

        resp = member_client.get(f'/api/v1/activities/project/{project.id}/?actor={u2.id}')
        assert resp.status_code == 200
        results = get_results(resp)
        assert len(results) == 1
        assert results[0]['actor'] == u2.id

    def test_project_activity_unauthenticated(self, api_client, make_project):
        """未认证不能访问项目动态流"""
        project = make_project()
        resp = api_client.get(f'/api/v1/activities/project/{project.id}/')
        assert resp.status_code == 401
