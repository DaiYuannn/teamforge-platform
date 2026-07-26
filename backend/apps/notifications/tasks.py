"""
通知定时任务
使用 Celery Beat 定时执行各类提醒任务
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import Notification
from .services import NotificationService

logger = logging.getLogger('apps.notifications')


@shared_task
def check_task_overdue():
    """
    任务延期 36 小时提醒
    每 3 小时执行一次，检查已逾期超过 36 小时且未提醒过的任务
    通知任务负责人和项目负责人
    """
    from apps.tasks.models import Task

    try:
        now = timezone.now()
        threshold = now - timedelta(hours=36)
        # 查找达到 36 小时逾期阈值、仍需处理且尚未成功登记提醒的任务。
        overdue_tasks = Task.objects.filter(
            status__in=[
                Task.Status.TODO,
                Task.Status.DOING,
                Task.Status.PENDING_REVIEW,
                Task.Status.NEED_HELP,
                Task.Status.OVERDUE,
            ],
            deadline__lte=threshold,
            overdue_reminded=False,
        ).select_related('assignee', 'project', 'project__leader')

        count = 0
        first_notified_task = None
        for task in overdue_tasks:
            notification_created = False
            title = f'任务延期提醒：{task.title}'
            content = (
                f'您的任务「{task.title}」已逾期超过 36 小时。\n'
                f'截止时间：{task.deadline.strftime("%Y-%m-%d %H:%M")}\n'
                f'所属项目：{task.project.name if task.project else "无"}\n'
                f'请尽快处理或更新任务状态。'
            )

            # 通知任务负责人
            if task.assignee:
                notification, _ = NotificationService.create_and_send_email(
                    recipient=task.assignee,
                    title=title,
                    content=content,
                    category='task',
                    ref_type='task',
                    ref_id=task.id,
                    priority='high',
                )
                notification_created = notification_created or notification is not None

            # 通知项目负责人
            if task.project and task.project.leader and task.project.leader != task.assignee:
                leader_title = f'项目任务延期提醒：{task.title}'
                leader_content = (
                    f'您项目「{task.project.name}」中的任务「{task.title}」已逾期超过 36 小时。\n'
                    f'任务负责人：{task.assignee.name if task.assignee else "未指派"}\n'
                    f'截止时间：{task.deadline.strftime("%Y-%m-%d %H:%M")}\n'
                    f'请关注任务进度。'
                )
                notification, _ = NotificationService.create_and_send_email(
                    recipient=task.project.leader,
                    title=leader_title,
                    content=leader_content,
                    category='task',
                    ref_type='task',
                    ref_id=task.id,
                    priority='high',
                )
                notification_created = notification_created or notification is not None

            # 只有至少一个渠道实际留下了通知记录，才停止后续重试。
            if notification_created:
                task.overdue_reminded = True
                task.save(update_fields=['overdue_reminded'])
                count += 1
                if first_notified_task is None:
                    first_notified_task = task

        # 群机器人推送（高优先级）
        if first_notified_task is not None:
            try:
                from apps.integrations.services import BotPushService
                BotPushService.push_task_reminder(
                    task_title=first_notified_task.title,
                    assignee_name=(
                        first_notified_task.assignee.name
                        if first_notified_task.assignee else ''
                    ),
                    project_name=(
                        first_notified_task.project.name
                        if first_notified_task.project else ''
                    ),
                    deadline=(
                        first_notified_task.deadline.strftime('%Y-%m-%d %H:%M')
                        if first_notified_task.deadline else ''
                    ),
                )
            except Exception as e:
                logger.warning('群机器人推送失败: %s', e)

        logger.info('任务延期提醒完成，共提醒 %d 个任务', count)
        return f'已完成 {count} 个任务的延期提醒'
    except Exception as e:
        logger.exception('任务延期提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def check_leader_update():
    """
    负责人 11 天未更新提醒
    每天 9:30 执行，检查进行中项目超过 11 天未更新的，通知项目负责人
    """
    from apps.projects.models import Project

    try:
        threshold = timezone.now() - timedelta(days=11)
        # 查找进行中且超过 11 天未更新的项目
        projects = Project.objects.filter(
            status='active',
        ).filter(
            Q(last_leader_update__lte=threshold)
            | Q(last_leader_update__isnull=True, created_at__lte=threshold)
        ).select_related('leader')

        count = 0
        for project in projects:
            if not project.leader:
                continue

            title = f'项目更新提醒：{project.name}'
            update_baseline = project.last_leader_update or project.created_at
            update_time = update_baseline.strftime('%Y-%m-%d %H:%M')
            content = (
                f'您负责的项目「{project.name}」已超过 11 天未更新进度。\n'
                f'上次更新时间：{update_time}\n'
                f'请及时进行项目进度打卡更新，保持项目活跃。'
            )

            NotificationService.create_and_send_email(
                recipient=project.leader,
                title=title,
                content=content,
                category='project',
                ref_type='project',
                ref_id=project.id,
                priority='normal',
            )
            count += 1

        logger.info('负责人更新提醒完成，共提醒 %d 个项目', count)
        return f'已完成 {count} 个项目的负责人更新提醒'
    except Exception as e:
        logger.exception('负责人更新提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def check_competition_deadlines():
    """
    比赛关键节点提醒。

    每天执行一次，在报名、材料提交、答辩和结果公布前 7/3/1 天及当天，
    通知项目负责人和项目成员；同一天重复执行不会重复创建通知。
    """
    from apps.competitions.models import Competition
    from apps.projects.models import ProjectMember
    from apps.users.models import User

    today = timezone.localdate()
    deadline_fields = {
        'register_date': '报名',
        'material_deadline': '材料提交',
        'defense_date': '比赛答辩',
        'result_date': '结果公布',
    }
    try:
        competitions = Competition.objects.filter(
            status__in=[
                Competition.Status.PREPARING,
                Competition.Status.ONGOING,
            ]
        ).select_related('project', 'project__leader')
        notification_count = 0
        for competition in competitions:
            recipient_ids = set(
                ProjectMember.objects.filter(
                    project=competition.project,
                    user__is_active=True,
                ).values_list('user_id', flat=True)
            )
            if competition.project.leader_id:
                recipient_ids.add(competition.project.leader_id)
            recipients = list(User.objects.filter(id__in=recipient_ids, is_active=True))
            if not recipients:
                continue

            for field_name, label in deadline_fields.items():
                deadline = getattr(competition, field_name)
                if deadline is None:
                    continue
                days_until = (deadline - today).days
                if days_until not in {7, 3, 1, 0}:
                    continue
                relative_text = '今天截止' if days_until == 0 else f'还有 {days_until} 天'
                title = f'比赛{label}提醒：{competition.name}'
                content = (
                    f'项目「{competition.project.name}」参加的「{competition.name}」'
                    f'{label}节点{relative_text}（{deadline:%Y-%m-%d}）。'
                    f'请及时核对任务与材料。'
                )
                ref_type = f'competition_{field_name}'
                already_notified_ids = set(
                    Notification.objects.filter(
                        recipient_id__in=recipient_ids,
                        related_object_type=ref_type,
                        related_object_id=competition.id,
                        created_at__date=today,
                    ).values_list('recipient_id', flat=True)
                )
                pending_recipients = [
                    user for user in recipients if user.id not in already_notified_ids
                ]
                notification_count += NotificationService.bulk_create_and_send_email(
                    recipients=pending_recipients,
                    title=title,
                    content=content,
                    category=Notification.NotificationType.COMPETITION,
                    ref_type=ref_type,
                    ref_id=competition.id,
                    priority=(
                        Notification.Priority.HIGH
                        if days_until <= 1
                        else Notification.Priority.NORMAL
                    ),
                )

        logger.info('比赛关键节点提醒完成，共创建 %d 条通知', notification_count)
        return f'已完成 {notification_count} 条比赛关键节点提醒'
    except Exception as e:
        logger.exception('比赛关键节点提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def remind_flexible_schedule():
    """
    灵活工作时间 15 天填写提醒
    每月 1 日和 16 日 10:00 执行，提醒未填写当前半月周期工时的学生
    """
    from apps.users.models import User
    from apps.members.models import FlexibleWorkSchedule
    from apps.members.periods import get_half_month_period

    try:
        today = timezone.now().date()
        period_start, period_end = get_half_month_period(today)

        # 已填写当前周期的成员
        filled_user_ids = FlexibleWorkSchedule.objects.filter(
            period_start=period_start
        ).values_list('user_id', flat=True)

        # 未填写的活跃学生
        unfilled_users = User.objects.filter(
            is_active=True,
            is_student=True,
        ).exclude(id__in=filled_user_ids)

        count = 0
        for user in unfilled_users:
            title = '灵活工作时间填写提醒'
            content = (
                f'{user.name}，您好：\n'
                f'当前半月周期（{period_start.strftime("%Y-%m-%d")} ~ '
                f'{period_end.strftime("%Y-%m-%d")}）的灵活工作时间尚未填写。\n'
                f'请及时登录系统填写可用工时、是否可线下、是否可承担紧急任务等信息，\n'
                f'以便项目任务合理分配。'
            )

            NotificationService.create_and_send_email(
                recipient=user,
                title=title,
                content=content,
                category=Notification.NotificationType.SCHEDULE,
                ref_type='flexible_work_schedule',
                ref_id=None,
                priority='normal',
            )
            count += 1

        logger.info('灵活工作时间提醒完成，共提醒 %d 名成员', count)
        return f'已完成 {count} 名成员的灵活工作时间提醒'
    except Exception as e:
        logger.exception('灵活工作时间提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def send_daily_notification_digest():
    """每天发送选择“每日摘要”的账户级合并邮件。"""
    return NotificationService.send_queued_digest('daily')


@shared_task
def send_weekly_notification_digest():
    """每周一发送选择“每周摘要”的账户级合并邮件。"""
    return NotificationService.send_queued_digest('weekly')


@shared_task
def check_ip_returns():
    """
    知识产权退回修改提醒
    每 6 小时执行，通知待修改退回记录的主导撰写人和申请执行人
    """
    from apps.intellectual_property.models import IPReturnRecord

    try:
        # 查找待修改的退回记录
        pending_returns = IPReturnRecord.objects.filter(
            result=IPReturnRecord.ReturnResult.PENDING,
        ).select_related(
            'application', 'application__main_writer',
            'application__applicant_executor',
        )

        count = 0
        for record in pending_returns:
            application = record.application
            notify_users = []
            # 主导撰写人
            if application.main_writer:
                notify_users.append(application.main_writer)
            # 申请执行人
            if application.applicant_executor and application.applicant_executor not in notify_users:
                notify_users.append(application.applicant_executor)

            title = f'知识产权退回修改提醒：{application.title}'
            content = (
                f'知识产权申请「{application.title}」（编号：{application.application_code}）'
                f'被退回修改，请尽快处理。\n'
                f'退回原因：{record.return_reason}\n'
                f'退回时间：{record.return_time.strftime("%Y-%m-%d %H:%M")}\n'
            )
            if record.modify_deadline:
                content += f'修改截止时间：{record.modify_deadline.strftime("%Y-%m-%d %H:%M")}\n'
            content += '请尽快完成修改并重新提交。'

            for user in notify_users:
                NotificationService.create_and_send_email(
                    recipient=user,
                    title=title,
                    content=content,
                    category=Notification.NotificationType.IP,
                    ref_type='ip_return',
                    ref_id=record.id,
                    priority='high',
                )
                count += 1

        logger.info('知识产权退回修改提醒完成，共提醒 %d 条记录', count)
        return f'已完成 {count} 条退回修改记录的提醒'
    except Exception as e:
        logger.exception('知识产权退回修改提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def check_ip_objections():
    """
    知识产权异议提醒
    每 6 小时执行（偏移 15 分钟），通知待处理异议的项目负责人和老师
    """
    from apps.intellectual_property.models import IPObjection

    try:
        # 查找待处理的异议
        pending = IPObjection.objects.filter(
            status=IPObjection.ObjectionStatus.PENDING,
        ).select_related(
            'application', 'application__related_project',
            'application__related_project__leader',
        )

        count = 0
        for obj in pending:
            application = obj.application
            notify_users = []

            # 项目负责人
            if application.related_project and application.related_project.leader:
                notify_users.append(application.related_project.leader)

            # 通知所有老师
            from apps.users.models import User
            teachers = User.objects.filter(global_role='teacher', is_active=True)
            for teacher in teachers:
                if teacher not in notify_users:
                    notify_users.append(teacher)

            title = f'知识产权异议待处理：{application.title}'
            content = (
                f'知识产权申请「{application.title}」（编号：{application.application_code}）'
                f'有一条新的异议待处理。\n'
                f'异议类型：{obj.get_objection_type_display()}\n'
                f'提出人：{obj.objector.name}\n'
                f'异议内容：{obj.content}\n'
                f'请尽快进行初审处理。'
            )

            for user in notify_users:
                NotificationService.create_and_send_email(
                    recipient=user,
                    title=title,
                    content=content,
                    category=Notification.NotificationType.IP,
                    ref_type='ip_objection',
                    ref_id=obj.id,
                    priority='high',
                )
                count += 1

        logger.info('知识产权异议提醒完成，共提醒 %d 条异议', count)
        return f'已完成 {count} 条异议的提醒'
    except Exception as e:
        logger.exception('知识产权异议提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def check_pending_contributions():
    """
    贡献记录待审核提醒
    每 6 小时执行（偏移 30 分钟），按项目分组通知各项目负责人
    """
    from apps.contributions.models import Contribution

    try:
        # 查找待审核的贡献记录
        pending = Contribution.objects.filter(
            status=Contribution.Status.PENDING,
            project__isnull=False,
        ).select_related('project', 'project__leader', 'user')

        # 按项目分组
        project_map = {}
        for contribution in pending:
            project = contribution.project
            if project not in project_map:
                project_map[project] = []
            project_map[project].append(contribution)

        count = 0
        for project, contributions in project_map.items():
            if not project.leader:
                continue

            title = f'贡献记录待审核提醒：{project.name}'
            content = (
                f'您项目「{project.name}」中有 {len(contributions)} 条贡献记录待审核：\n'
            )
            for c in contributions[:10]:  # 最多列出 10 条
                content += (
                    f'- {c.user.name} - {c.get_contribution_type_display()}'
                    f'（{c.content or c.description}）\n'
                )
            if len(contributions) > 10:
                content += f'... 共 {len(contributions)} 条\n'
            content += '请尽快登录系统进行审核。'

            NotificationService.create_and_send_email(
                recipient=project.leader,
                title=title,
                content=content,
                category=Notification.NotificationType.CONTRIBUTION,
                ref_type='contribution',
                ref_id=project.id,
                priority='normal',
            )
            count += 1

        logger.info('贡献记录待审核提醒完成，共提醒 %d 个项目', count)
        return f'已完成 {count} 个项目的贡献待审核提醒'
    except Exception as e:
        logger.exception('贡献记录待审核提醒执行失败: %s', e)
        return f'执行失败: {e}'


@shared_task
def check_sensitive_requests():
    """
    敏感资料申请待审批提醒
    每 6 小时执行（偏移 45 分钟），通知审批人（敏感审批人/管理员）
    """
    from apps.sensitive.models import SensitiveAccessRequest
    from apps.users.models import User

    try:
        # 查找待审批的申请
        pending = SensitiveAccessRequest.objects.filter(
            status=SensitiveAccessRequest.Status.PENDING,
        ).select_related('sensitive_data', 'applicant')

        if not pending.exists():
            return '无待审批的敏感资料申请'

        count = 0
        # 通知所有敏感审批人和系统管理员
        approvers = User.objects.filter(
            global_role__in=['sens_approver', 'sys_admin'],
            is_active=True,
        )

        title = f'敏感资料申请待审批提醒（{pending.count()} 条）'
        content = (
            f'当前有 {pending.count()} 条敏感资料访问申请待审批：\n'
        )
        for req in pending[:10]:
            content += (
                f'- {req.applicant.name} 申请访问「{req.sensitive_data.title}」'
                f'（{req.created_at.strftime("%Y-%m-%d %H:%M")}）\n'
            )
        if pending.count() > 10:
            content += f'... 共 {pending.count()} 条\n'
        content += '请尽快登录系统进行审批。'

        for approver in approvers:
            NotificationService.create_and_send_email(
                recipient=approver,
                title=title,
                content=content,
                category=Notification.NotificationType.SENSITIVE,
                ref_type='sensitive_request',
                ref_id=None,
                priority='high',
            )
            count += 1

        logger.info('敏感资料申请待审批提醒完成，共提醒 %d 名审批人', count)
        return f'已完成 {count} 名审批人的提醒'
    except Exception as e:
        logger.exception('敏感资料申请待审批提醒执行失败: %s', e)
        return f'执行失败: {e}'
