"""通知偏好、比赛期限和邮件真实发送结果。"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.competitions.models import Competition
from apps.notifications.email_service import send_notification_email
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService, should_notify_user
from apps.notifications.tasks import check_competition_deadlines
from apps.users.models import UserPreference


@pytest.mark.django_db
class TestNotificationPreferences:
    def test_disabled_category_blocks_notification(self, make_user):
        user = make_user(email='notify-disabled@test.com')
        UserPreference.objects.create(
            user=user,
            notification_preferences={'categories': {'finance': False}},
        )
        notification = NotificationService.create_notification(
            recipient=user,
            title='经费更新',
            content='内容',
            category='finance',
        )
        assert notification is None
        assert Notification.objects.filter(recipient=user).count() == 0

    def test_email_disabled_falls_back_to_inapp(self, make_user):
        user = make_user(email='notify-channel@test.com')
        UserPreference.objects.create(
            user=user,
            notification_preferences={
                'channels': {'email': False, 'inapp': True},
            },
        )
        with patch(
            'apps.notifications.services.send_notification_email'
        ) as email_mock:
            notification, sent = NotificationService.create_and_send_email(
                recipient=user,
                title='项目提醒',
                content='内容',
                category='project',
            )
        assert notification is not None
        assert notification.channel == Notification.Channel.INAPP
        assert sent is False
        email_mock.assert_not_called()

    def test_approval_preference_controls_sensitive_and_ip(self, make_user):
        user = make_user(email='notify-approval@test.com')
        UserPreference.objects.create(
            user=user,
            notification_preferences={'categories': {'approval': False}},
        )
        assert should_notify_user(user, category='sensitive') is False
        assert should_notify_user(user, category='ip') is False

    def test_system_and_schedule_categories_are_independently_configurable(
        self, make_user
    ):
        user = make_user(email='notify-business-categories@test.com')
        UserPreference.objects.create(
            user=user,
            notification_preferences={
                'categories': {'system': True, 'schedule': False},
            },
        )

        assert should_notify_user(user, category='announcement') is True
        assert should_notify_user(user, category='schedule') is False

    def test_quiet_hours_suppress_normal_email_not_inapp(self, make_user):
        user = make_user(email='notify-quiet@test.com')
        UserPreference.objects.create(
            user=user,
            notification_preferences={
                'quiet_hours': {
                    'enabled': True,
                    'start': '22:00',
                    'end': '07:00',
                }
            },
        )
        fixed_now = timezone.make_aware(datetime(2026, 7, 26, 23, 30))
        assert should_notify_user(
            user,
            category='project',
            channel='email',
            priority='normal',
            now=fixed_now,
        ) is False
        assert should_notify_user(
            user,
            category='project',
            channel='inapp',
            priority='normal',
            now=fixed_now,
        ) is True
        assert should_notify_user(
            user,
            category='project',
            channel='email',
            priority='high',
            now=fixed_now,
        ) is True


class TestEmailDeliveryResult:
    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('apps.notifications.email_service.send_mail', return_value=0)
    def test_zero_delivery_is_failure(self, send_mail_mock):
        assert send_notification_email(
            'member@example.com', '标题', '内容'
        ) is False
        assert send_mail_mock.call_args.kwargs['fail_silently'] is False

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('apps.notifications.email_service.send_mail', return_value=1)
    def test_one_delivery_is_success(self, send_mail_mock):
        assert send_notification_email(
            'member@example.com', '标题', '内容'
        ) is True


@pytest.mark.django_db
class TestPersistedEmailDelivery:
    @patch('apps.notifications.services.send_notification_email', return_value=True)
    def test_immediate_success_is_persisted(self, email_mock, make_user):
        user = make_user(email='delivery-success@test.com')

        notification, sent = NotificationService.create_and_send_email(
            recipient=user,
            title='即时通知',
            content='发送成功',
            category='task',
        )

        assert sent is True
        notification.refresh_from_db()
        assert (
            notification.email_delivery_status
            == Notification.EmailDeliveryStatus.SENT
        )
        assert notification.email_attempted_at is not None
        assert notification.email_sent_at is not None
        assert notification.email_delivery_error == ''
        email_mock.assert_called_once()

    @patch('apps.notifications.services.send_notification_email', return_value=False)
    def test_immediate_failure_is_persisted(self, email_mock, make_user):
        user = make_user(email='delivery-failure@test.com')

        notification, sent = NotificationService.create_and_send_email(
            recipient=user,
            title='即时通知',
            content='发送失败',
            category='project',
        )

        assert sent is False
        notification.refresh_from_db()
        assert (
            notification.email_delivery_status
            == Notification.EmailDeliveryStatus.FAILED
        )
        assert notification.email_attempted_at is not None
        assert notification.email_sent_at is None
        assert notification.email_delivery_error
        email_mock.assert_called_once()

    @patch('apps.notifications.services.send_notification_email', return_value=True)
    def test_daily_digest_queues_then_sends_one_account_summary(
        self, email_mock, make_user
    ):
        user = make_user(email='delivery-digest@test.com')
        UserPreference.objects.create(
            user=user,
            notification_preferences={'digest': 'daily'},
        )
        first, first_sent = NotificationService.create_and_send_email(
            recipient=user,
            title='任务提醒',
            content='第一条',
            category='task',
        )
        second, second_sent = NotificationService.create_and_send_email(
            recipient=user,
            title='项目提醒',
            content='第二条',
            category='project',
        )

        assert first_sent is second_sent is False
        assert email_mock.call_count == 0
        assert first.email_delivery_status == Notification.EmailDeliveryStatus.QUEUED
        assert second.email_delivery_status == Notification.EmailDeliveryStatus.QUEUED

        stats = NotificationService.send_queued_digest(
            'daily',
            now=timezone.make_aware(datetime(2026, 7, 26, 12, 0)),
        )

        assert stats == {
            'recipients': 1,
            'sent': 2,
            'failed': 0,
            'suppressed': 0,
        }
        assert email_mock.call_count == 1
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.email_delivery_status == Notification.EmailDeliveryStatus.SENT
        assert second.email_delivery_status == Notification.EmailDeliveryStatus.SENT
        assert first.email_sent_at is not None
        assert second.email_sent_at is not None


@pytest.mark.django_db
class TestCompetitionDeadlineNotifications:
    def test_deadline_notification_and_daily_dedup(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='competition-notify@test.com')
        from apps.projects.models import ProjectMember
        ProjectMember.objects.create(project=project, user=member)
        Competition.objects.create(
            project=project,
            name='创新创业大赛',
            status=Competition.Status.PREPARING,
            material_deadline=timezone.localdate() + timedelta(days=3),
        )
        first = check_competition_deadlines()
        assert '2' in first
        assert Notification.objects.filter(
            recipient__in=[project.leader, member],
            notification_type=Notification.NotificationType.COMPETITION,
        ).count() == 2

        second = check_competition_deadlines()
        assert '0' in second
        assert Notification.objects.filter(
            notification_type=Notification.NotificationType.COMPETITION,
        ).count() == 2
