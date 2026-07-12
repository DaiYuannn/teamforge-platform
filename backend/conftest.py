"""
Pytest 全局配置和 fixtures
提供各角色用户、API 客户端、通用测试数据
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User

User = get_user_model()


# ========== API 客户端 ==========

@pytest.fixture
def api_client():
    """未认证 API 客户端"""
    return APIClient()


@pytest.fixture
def auth_client(api_client, make_user):
    """已认证普通成员客户端"""
    user = make_user(global_role='member', email='member@test.com')
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


def _role_client_factory(api_client, make_user):
    """创建指定角色的认证客户端"""
    def _create(role, email=None):
        email = email or f'{role}@test.com'
        user = make_user(global_role=role, email=email)
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        api_client.user = user
        return api_client
    return _create


@pytest.fixture
def admin_client(api_client, make_user):
    """系统管理员客户端"""
    user = make_user(global_role='sys_admin', email='admin@test.com', is_staff=True, is_superuser=True)
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def teacher_client(api_client, make_user):
    """老师客户端"""
    user = make_user(global_role='teacher', email='teacher@test.com')
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def leader_client(api_client, make_user):
    """项目负责人客户端"""
    user = make_user(global_role='member', email='leader@test.com')
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def approver_client(api_client, make_user):
    """敏感审批人客户端"""
    user = make_user(global_role='sens_approver', email='approver@test.com')
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def member_client(api_client, make_user):
    """普通成员客户端"""
    user = make_user(email='member_cli@test.com')
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


# ========== 用户工厂 ==========

@pytest.fixture
def make_user(db):
    """创建用户的工厂函数"""
    created = []
    counter = [0]

    def _make(
        email=None,
        password='TestPass123!',
        global_role='member',
        name=None,
        is_staff=False,
        is_superuser=False,
        **extra,
    ):
        counter[0] += 1
        email = email or f'user{counter[0]}@test.com'
        name = name or f'测试用户{counter[0]}'
        user = User.objects.create_user(
            email=email,
            username=email,
            password=password,
            name=name,
            global_role=global_role,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra,
        )
        created.append(user)
        return user

    return _make


@pytest.fixture
def admin_user(make_user):
    return make_user(
        email='admin@test.com',
        global_role='sys_admin',
        name='系统管理员',
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def teacher_user(make_user):
    return make_user(email='teacher@test.com', global_role='teacher', name='老师')


@pytest.fixture
def member_user(make_user):
    return make_user(email='member@test.com', global_role='member', name='普通成员')


@pytest.fixture
def approver_user(make_user):
    return make_user(email='approver@test.com', global_role='sens_approver', name='审批人')


# ========== 项目相关 ==========

@pytest.fixture
def make_project(db, make_user):
    """创建项目的工厂函数"""
    from apps.projects.models import Project, ProjectMember
    created = []
    counter = [0]

    def _make(leader=None, name=None, code=None, current_stage=1, status='active', **extra):
        counter[0] += 1
        leader = leader or make_user(
            email=f'leader{counter[0]}@test.com',
            global_role='member',
            name=f'负责人{counter[0]}',
        )
        project = Project.objects.create(
            name=name or f'测试项目{counter[0]}',
            code=code or f'PROJ-{counter[0]:04d}',
            leader=leader,
            current_stage=current_stage,
            status=status,
            **extra,
        )
        ProjectMember.objects.create(
            project=project,
            user=leader,
            role_in_project='leader',
        )
        created.append(project)
        return project

    return _make


@pytest.fixture
def make_task(db, make_project):
    """创建任务的工厂函数"""
    from apps.tasks.models import Task
    counter = [0]

    def _make(project=None, assignee=None, title=None, status='todo', **extra):
        counter[0] += 1
        project = project or make_project()
        assignee = assignee or project.leader
        return Task.objects.create(
            project=project,
            title=title or f'测试任务{counter[0]}',
            assignee=assignee,
            status=status,
            **extra,
        )

    return _make


@pytest.fixture
def make_finance(db, make_project):
    """创建经费记录的工厂函数"""
    from apps.finance.models import FinanceExpense
    counter = [0]

    def _make(project=None, amount=100, **extra):
        counter[0] += 1
        project = project or make_project()
        return FinanceExpense.objects.create(
            project=project,
            amount=amount,
            title=extra.pop('title', f'测试经费{counter[0]}'),
            expense_date=extra.pop('expense_date', '2026-07-07'),
            **extra,
        )

    return _make


@pytest.fixture
def make_file(db, make_project, make_user):
    """创建文件记录的工厂函数"""
    from apps.files.models import FileAsset
    counter = [0]

    def _make(project=None, uploader=None, name=None, level='public', **extra):
        counter[0] += 1
        project = project or make_project()
        uploader = uploader or make_user(email=f'uploader{counter[0]}@test.com')
        return FileAsset.objects.create(
            project=project,
            name=name or f'测试文件{counter[0]}.pdf',
            file='dummy/path.pdf',
            level=level,
            size=1024,
            content_type='application/pdf',
            uploader=uploader,
            **extra,
        )

    return _make


@pytest.fixture
def make_sensitive_data(db, make_project, make_user):
    """创建敏感数据的工厂函数"""
    from apps.sensitive.models import SensitiveData
    counter = [0]

    def _make(uploader=None, project=None, title=None, data_type='id_card', **extra):
        counter[0] += 1
        project = project or make_project()
        uploader = uploader or make_user(email=f'sens_owner{counter[0]}@test.com')
        sd = SensitiveData.objects.create(
            title=title or f'敏感数据{counter[0]}',
            data_type=data_type,
            project=project,
            uploader=uploader,
            **extra,
        )
        sd.encrypt_content('测试敏感明文内容')
        return sd

    return _make


# ========== 通用工具 ==========

@pytest.fixture
def jwt_token(make_user):
    """获取 JWT token"""
    user = make_user(email='login@test.com', global_role='member')
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': user,
    }
