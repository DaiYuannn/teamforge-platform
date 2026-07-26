"""
P10: Celery 定时任务验证测试
- 验证 8 个通知定时任务可正常调用（不抛异常）
- 验证 check_task_overdue 能发现逾期任务
- 验证 check_leader_update 能发现长期未更新项目
- 通过 mock send_notification_email / BotPushService 避免真实发送
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.notifications.tasks import (
    check_task_overdue,
    check_leader_update,
    check_competition_deadlines,
    remind_flexible_schedule,
    check_ip_returns,
    check_ip_objections,
    check_pending_contributions,
    check_sensitive_requests,
)
from apps.notifications.models import Notification
from apps.users.models import UserPreference


# 全部 8 个任务
ALL_TASKS = [
    check_task_overdue,
    check_leader_update,
    check_competition_deadlines,
    remind_flexible_schedule,
    check_ip_returns,
    check_ip_objections,
    check_pending_contributions,
    check_sensitive_requests,
]


@pytest.fixture
def mock_senders():
    """统一 mock 邮件发送与群机器人推送，避免真实外部调用"""
    with patch('apps.notifications.services.send_notification_email', return_value=True) as email_mock, \
         patch('apps.integrations.services.BotPushService') as bot_mock:
        yield {'email': email_mock, 'bot': bot_mock}


@pytest.mark.integration
@pytest.mark.django_db
class TestCeleryTasksCallable:
    """所有定时任务均可同步调用且不抛异常"""

    @pytest.mark.parametrize('task', ALL_TASKS, ids=lambda t: t.name)
    def test_task_callable_without_error(self, task, mock_senders):
        """每个任务都能被调用并返回字符串结果"""
        result = task()
        assert isinstance(result, str)
        # 不应返回失败信息
        assert '执行失败' not in result

    def test_task_apply_runs_synchronously(self, mock_senders):
        """通过 .apply() 同步执行也正常"""
        result = check_sensitive_requests.apply().get()
        assert isinstance(result, str)


@pytest.mark.integration
@pytest.mark.django_db
class TestCheckTaskOverdue:
    """check_task_overdue 任务测试"""

    def test_finds_overdue_task(self, mock_senders, make_task, make_user):
        """能发现逾期超过 36 小时的待办任务并标记已提醒"""
        assignee = make_user(email='assignee@overdue.com', name='负责人甲')
        # 截止时间为 48 小时前（超过 36 小时阈值）
        deadline = timezone.now() - timedelta(hours=48)
        task = make_task(
            assignee=assignee,
            title='逾期任务',
            status='todo',
            deadline=deadline,
            overdue_reminded=False,
        )

        result = check_task_overdue()

        # 任务被标记为已提醒
        task.refresh_from_db()
        assert task.overdue_reminded is True
        # 创建了站内通知（邮件渠道）给负责人
        assert Notification.objects.filter(recipient=assignee).exists()
        # 返回结果包含提醒数量
        assert '1' in result or '提醒' in result

    def test_skips_recently_overdue_task(self, mock_senders, make_task):
        """逾期不足 36 小时的任务不会被提醒"""
        deadline = timezone.now() - timedelta(hours=12)
        task = make_task(
            title='刚逾期任务',
            status='todo',
            deadline=deadline,
            overdue_reminded=False,
        )

        check_task_overdue()

        task.refresh_from_db()
        assert task.overdue_reminded is False

    def test_reminds_at_exactly_36_hour_threshold(
        self, mock_senders, make_task
    ):
        fixed_now = timezone.now().replace(microsecond=0)
        task = make_task(
            title='刚好达到提醒阈值',
            status='pending_review',
            deadline=fixed_now - timedelta(hours=36),
            overdue_reminded=False,
        )

        with patch(
            'apps.notifications.tasks.timezone.now',
            return_value=fixed_now,
        ):
            check_task_overdue()

        task.refresh_from_db()
        assert task.overdue_reminded is True

    def test_keeps_retryable_when_all_user_channels_are_disabled(
        self, mock_senders, make_task, make_project, make_user
    ):
        assignee = make_user(email='overdue-disabled@test.com')
        project = make_project(leader=assignee)
        UserPreference.objects.create(
            user=assignee,
            notification_preferences={
                'categories': {'task': True},
                'channels': {'in_app': False, 'email': False},
            },
        )
        task = make_task(
            project=project,
            assignee=assignee,
            title='等待账户重新开启通知',
            status='need_help',
            deadline=timezone.now() - timedelta(hours=48),
            overdue_reminded=False,
        )

        check_task_overdue()

        task.refresh_from_db()
        assert task.overdue_reminded is False
        assert not Notification.objects.filter(recipient=assignee).exists()

    def test_skips_already_reminded(self, mock_senders, make_task):
        """已提醒过的任务不会重复提醒"""
        deadline = timezone.now() - timedelta(hours=48)
        task = make_task(
            title='已提醒任务',
            status='todo',
            deadline=deadline,
            overdue_reminded=True,
        )

        check_task_overdue()

        task.refresh_from_db()
        assert task.overdue_reminded is True

    def test_skips_done_task(self, mock_senders, make_task):
        """已完成的任务即使逾期也不会被提醒"""
        deadline = timezone.now() - timedelta(hours=48)
        task = make_task(
            title='已完成任务',
            status='done',
            deadline=deadline,
            overdue_reminded=False,
        )

        check_task_overdue()

        task.refresh_from_db()
        assert task.overdue_reminded is False

    def test_notifies_project_leader(self, mock_senders, make_task, make_project, make_user):
        """任务逾期时同时通知项目负责人（与负责人不同时）"""
        leader = make_user(email='leader@proj.com', name='项目负责人')
        assignee = make_user(email='assignee2@proj.com', name='执行人')
        project = make_project(leader=leader)
        deadline = timezone.now() - timedelta(hours=48)
        make_task(
            project=project,
            assignee=assignee,
            title='需通知负责人',
            status='todo',
            deadline=deadline,
            overdue_reminded=False,
        )

        check_task_overdue()

        # 负责人也收到通知
        assert Notification.objects.filter(recipient=leader).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestCheckLeaderUpdate:
    """check_leader_update 任务测试"""

    def test_finds_stale_project(self, mock_senders, make_project):
        """能发现超过 11 天未更新的进行中项目"""
        project = make_project()
        # 设置负责人最近更新时间为 15 天前
        project.last_leader_update = timezone.now() - timedelta(days=15)
        project.save()

        result = check_leader_update()

        # 负责人收到通知
        assert Notification.objects.filter(recipient=project.leader).exists()
        assert '完成' in result or '提醒' in result

    def test_skips_recently_updated_project(self, mock_senders, make_project):
        """最近更新过的项目不会被提醒"""
        project = make_project()
        project.last_leader_update = timezone.now() - timedelta(days=3)
        project.save()

        check_leader_update()

        assert not Notification.objects.filter(recipient=project.leader).exists()

    def test_new_project_without_update_gets_full_eleven_days(self, mock_senders, make_project):
        """尚未打卡的新项目以创建时间起算，不会立即被判定为滞后"""
        project = make_project()
        project.last_leader_update = None
        project.save(update_fields=['last_leader_update'])

        check_leader_update()

        assert not Notification.objects.filter(recipient=project.leader).exists()

    def test_old_project_without_update_is_reminded(self, mock_senders, make_project):
        """从未打卡的老项目在创建满 11 天后会被提醒"""
        project = make_project()
        project.last_leader_update = None
        project.save(update_fields=['last_leader_update'])
        project.__class__.objects.filter(pk=project.pk).update(
            created_at=timezone.now() - timedelta(days=12),
        )

        check_leader_update()

        assert Notification.objects.filter(recipient=project.leader).exists()

    def test_skips_closed_project(self, mock_senders, make_project):
        """已关闭的项目即使长期未更新也不会被提醒"""
        project = make_project(status='closed')
        project.last_leader_update = timezone.now() - timedelta(days=30)
        project.save()

        check_leader_update()

        assert not Notification.objects.filter(recipient=project.leader).exists()

    def test_skips_project_without_leader(self, mock_senders, make_project, make_user):
        """没有负责人的项目会被跳过（不报错）"""
        # make_project 总是会创建 leader，这里仅验证任务不抛异常
        project = make_project()
        project.last_leader_update = timezone.now() - timedelta(days=15)
        project.save()

        result = check_leader_update()
        assert isinstance(result, str)
