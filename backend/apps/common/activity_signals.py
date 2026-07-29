"""把关键业务变化统一沉淀到团队动态。"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .activity_models import Activity
from .activity_services import log_activity


def _root_team(team):
    return getattr(team, 'parent', None) or team


def _remember_previous_status(sender, instance):
    instance._activity_previous_status = (
        sender.objects.filter(pk=instance.pk)
        .values_list('status', flat=True)
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender='projects.Project')
def log_project_change(sender, instance, created, **kwargs):
    activity_type = (
        Activity.Type.PROJECT_CREATED
        if created
        else (
            Activity.Type.PROJECT_CLOSED
            if instance.status == instance.Status.CLOSED
            else Activity.Type.PROJECT_UPDATED
        )
    )
    log_activity(
        activity_type,
        actor=instance.leader,
        project=instance,
        target_type='project',
        target_id=instance.pk,
        description=(
            f'创建项目“{instance.name}”'
            if created
            else f'更新项目“{instance.name}”（{instance.get_status_display()}）'
        ),
        metadata={
            'status': instance.status,
            'stage': instance.current_stage,
        },
    )


@receiver(post_save, sender='tasks.Task')
def log_task_change(sender, instance, created, **kwargs):
    if created:
        activity_type = Activity.Type.TASK_CREATED
        description = f'创建任务“{instance.title}”'
    elif instance.status == instance.Status.DONE:
        activity_type = Activity.Type.TASK_COMPLETED
        description = f'完成任务“{instance.title}”'
    else:
        activity_type = Activity.Type.TASK_UPDATED
        description = f'更新任务“{instance.title}”'
    log_activity(
        activity_type,
        actor=instance.creator or instance.assignee,
        project=instance.project,
        target_type='task',
        target_id=instance.pk,
        description=description,
        metadata={'status': instance.status},
    )


@receiver(post_save, sender='files.FileAsset')
def log_file_upload(sender, instance, created, **kwargs):
    if not created:
        return
    log_activity(
        Activity.Type.FILE_UPLOADED,
        actor=instance.uploader,
        project=instance.project,
        target_type='file',
        target_id=instance.pk,
        description=f'上传文件“{instance.name}”',
        metadata={'level': instance.level, 'size': instance.size},
    )


@receiver(post_save, sender='tasks.TaskComment')
def log_task_comment(sender, instance, created, **kwargs):
    if not created:
        return
    log_activity(
        Activity.Type.COMMENT_CREATED,
        actor=instance.author,
        project=instance.task.project,
        target_type='task_comment',
        target_id=instance.pk,
        description=f'评论任务“{instance.task.title}”',
    )


@receiver(pre_save, sender='common.TeamMember')
def remember_team_member_status(sender, instance, **kwargs):
    _remember_previous_status(sender, instance)


@receiver(post_save, sender='common.TeamMember')
def log_team_member_change(sender, instance, created, **kwargs):
    active_statuses = {
        instance.Status.ACTIVE,
        instance.Status.ON_LEAVE,
    }
    previous_status = getattr(instance, '_activity_previous_status', None)
    joined = (
        instance.status in active_statuses
        and (
            created
            or previous_status not in active_statuses
        )
    )
    left = (
        not created
        and previous_status in active_statuses
        and instance.status not in active_statuses
    )
    if not joined and not left:
        return
    log_activity(
        (
            Activity.Type.MEMBER_JOINED
            if joined
            else Activity.Type.MEMBER_LEFT
        ),
        actor=instance.user,
        organization=_root_team(instance.team),
        target_type='team_member',
        target_id=instance.pk,
        description=(
            f'{instance.user.name} 加入“{instance.team.name}”'
            if joined
            else f'{instance.user.name} 离开“{instance.team.name}”'
        ),
        metadata={
            'team_id': instance.team_id,
            'team_name': instance.team.name,
            'role': instance.role,
            'status': instance.status,
        },
    )


@receiver(post_save, sender='competitions.Competition')
def log_competition_change(sender, instance, created, **kwargs):
    if created:
        activity_type = Activity.Type.COMPETITION_CREATED
        action = '创建'
    elif instance.is_awarded:
        activity_type = Activity.Type.COMPETITION_AWARDED
        action = '更新获奖结果'
    else:
        activity_type = Activity.Type.COMPETITION_UPDATED
        action = '更新'
    log_activity(
        activity_type,
        actor=instance.project.leader,
        project=instance.project,
        target_type='competition',
        target_id=instance.pk,
        description=(
            f'{action}比赛参赛条目“'
            f'{instance.entry_name or instance.name}”'
        ),
        metadata={
            'event_id': instance.event_id,
            'entry_name': instance.entry_name,
            'status': instance.status,
            'award_level': instance.award_level,
        },
    )


@receiver(post_save, sender='competitions.CompetitionAward')
def log_competition_award(sender, instance, created, **kwargs):
    if not created:
        return
    log_activity(
        Activity.Type.COMPETITION_AWARDED,
        actor=instance.competition.project.leader,
        project=instance.competition.project,
        target_type='competition_award',
        target_id=instance.pk,
        description=(
            f'登记“{instance.competition.entry_name or instance.competition.name}”'
            f'获奖：{instance.award_name}'
        ),
        metadata={
            'competition_id': instance.competition_id,
            'award_level': instance.award_level,
        },
    )


@receiver(pre_save, sender='finance.FinanceExpense')
def remember_finance_expense_status(sender, instance, **kwargs):
    instance._activity_previous_status = (
        sender.all_objects.filter(pk=instance.pk)
        .values_list('reimbursement_status', flat=True)
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender='finance.FinanceExpense')
def log_finance_expense(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_activity_previous_status', None)
    if not created and previous_status == instance.reimbursement_status:
        return
    actor = (
        getattr(instance, 'paid_by', None)
        or getattr(instance, 'reviewer', None)
        or getattr(instance, 'applied_by', None)
        or instance.spender
    )
    log_activity(
        Activity.Type.FINANCE_EXPENSE,
        actor=actor,
        project=instance.project,
        target_type='finance_expense',
        target_id=instance.pk,
        description=(
            f'{"登记" if created else "更新"}支出'
            f'“{instance.title}”：{instance.amount} 元'
        ),
        metadata={
            'amount': str(instance.amount),
            'status': instance.reimbursement_status,
        },
    )


@receiver(pre_save, sender='finance.FinancePayment')
def remember_finance_payment_status(sender, instance, **kwargs):
    _remember_previous_status(sender, instance)


@receiver(post_save, sender='finance.FinancePayment')
def log_finance_payment(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_activity_previous_status', None)
    visible_statuses = {
        instance.Status.COMPLETED,
        instance.Status.FAILED,
        instance.Status.REVERSED,
    }
    if (
        instance.status not in visible_statuses
        or (not created and previous_status == instance.status)
    ):
        return
    status_action = {
        instance.Status.COMPLETED: '完成付款',
        instance.Status.FAILED: '登记付款异常',
        instance.Status.REVERSED: '冲正付款',
    }[instance.status]
    log_activity(
        Activity.Type.FINANCE_PAYMENT,
        actor=instance.paid_by,
        project=instance.expense.project,
        target_type='finance_payment',
        target_id=instance.pk,
        description=(
            f'{status_action}“{instance.expense.title}”：'
            f'{instance.amount} 元'
        ),
        metadata={
            'expense_id': instance.expense_id,
            'amount': str(instance.amount),
            'status': instance.status,
            'recipient_id': instance.recipient_id,
            'counts_as_team_expense': instance.status == instance.Status.COMPLETED,
        },
    )


@receiver(pre_save, sender='finance.FinanceInternalTransfer')
def remember_finance_transfer_status(sender, instance, **kwargs):
    _remember_previous_status(sender, instance)


@receiver(post_save, sender='finance.FinanceInternalTransfer')
def log_finance_transfer(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_activity_previous_status', None)
    visible_statuses = {
        instance.Status.COMPLETED,
        instance.Status.FAILED,
    }
    if (
        instance.status not in visible_statuses
        or (not created and previous_status == instance.status)
    ):
        return
    source_name = (
        instance.from_user.name
        if instance.from_user_id
        else instance.source_label
    )
    status_action = (
        '完成内部转付'
        if instance.status == instance.Status.COMPLETED
        else '登记内部转付异常'
    )
    log_activity(
        Activity.Type.FINANCE_TRANSFER,
        actor=instance.recorded_by,
        project=instance.project,
        target_type='finance_internal_transfer',
        target_id=instance.pk,
        description=(
            f'{status_action}：{source_name or "外部来源"} → '
            f'{instance.to_user.name}，{instance.amount} 元'
        ),
        metadata={
            'amount': str(instance.amount),
            'status': instance.status,
            'from_user_id': instance.from_user_id,
            'to_user_id': instance.to_user_id,
            'counts_as_income_or_expense': False,
        },
    )


@receiver(post_save, sender='finance.FinanceIncome')
def log_finance_income(sender, instance, created, **kwargs):
    log_activity(
        Activity.Type.FINANCE_INCOME,
        actor=instance.recorded_by,
        project=instance.project,
        target_type='finance_income',
        target_id=instance.pk,
        description=f'登记收入“{instance.title}”：{instance.amount} 元',
        metadata={
            'amount': str(instance.amount),
            'income_type': instance.income_type,
            'stage': getattr(instance, 'stage', 'received'),
        },
    )


@receiver(post_save, sender='intellectual_property.IntellectualPropertyApplication')
def log_ip_change(sender, instance, created, **kwargs):
    authorized_statuses = {'authorized', 'archived'}
    if created:
        activity_type = Activity.Type.IP_CREATED
        action = '创建'
    elif instance.status in authorized_statuses:
        activity_type = Activity.Type.IP_AUTHORIZED
        action = '登记授权'
    else:
        activity_type = Activity.Type.IP_UPDATED
        action = '更新'
    log_activity(
        activity_type,
        actor=instance.created_by,
        project=instance.related_project,
        target_type='intellectual_property',
        target_id=instance.pk,
        description=f'{action}成果“{instance.title}”',
        metadata={'status': instance.status, 'ip_type': instance.ip_type},
    )


@receiver(post_save, sender='notifications.Announcement')
def log_announcement_publish(sender, instance, created, **kwargs):
    if instance.status != instance.Status.PUBLISHED:
        return
    log_activity(
        Activity.Type.ANNOUNCEMENT_PUBLISHED,
        actor=instance.author,
        organization=instance.organization,
        target_type='announcement',
        target_id=instance.pk,
        description=f'发布公告“{instance.title}”',
        metadata={
            'audience': instance.audience,
            'category': instance.category,
        },
    )
