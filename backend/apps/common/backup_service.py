"""演示环境备份包的创建、校验、列举与恢复。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import Q
from django.utils import timezone


BACKUP_ID_PATTERN = re.compile(r'^demo-\d{8}-\d{6}(?:-\d{3})?$')
SUPPORTED_BACKUP_SCHEMAS = {
    'team-management-demo-backup-v1',
    'team-management-demo-backup-v2',
}
MAX_DEMO_BACKUP_SIZE = 512 * 1024 * 1024
DEMO_ACCOUNT_EMAILS = (
    'admin@demo.com',
    'teacher1@demo.com',
    'teacher2@demo.com',
    'teacher3@demo.com',
    'teacher4@demo.com',
    'leader1@demo.com',
    'leader2@demo.com',
    'leader3@demo.com',
    'leader4@demo.com',
    'leader5@demo.com',
    'contributor1@demo.com',
    'contributor2@demo.com',
    *(f'member{index}@demo.com' for index in range(1, 36)),
)
DEMO_MARKER = '【团队演示】'
DEMO_TEAM_CODE = 'TEAM-DEMO-ORG'


class DemoBackupError(Exception):
    pass


def _demo_projects():
    """Return projects managed by the current deterministic full demo seed."""
    from apps.projects.models import Project

    return Project.objects.filter(code__startswith='TEAM-DEMO-')


def _demo_users():
    """Return the exact account set recreated by ``seed_demo_data``."""
    from apps.users.models import User

    return User.objects.filter(email__in=DEMO_ACCOUNT_EMAILS)


def backup_root() -> Path:
    root = Path(
        getattr(
            settings,
            'DEMO_BACKUP_ROOT',
            Path(settings.BASE_DIR) / 'demo_backups',
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_backup_path(backup_id: str) -> Path:
    if not BACKUP_ID_PATTERN.fullmatch(backup_id):
        raise DemoBackupError('备份编号格式无效')
    path = (backup_root() / f'{backup_id}.zip').resolve()
    if path.parent != backup_root():
        raise DemoBackupError('备份路径无效')
    return path


def _snapshot_payload() -> dict:
    """生成不含密码和敏感正文的演示业务快照。"""
    from apps.audit.models import OperationLog
    from apps.common.team_models import Team, TeamMember, TeamMembershipEvent
    from apps.competitions.models import (
        Competition,
        CompetitionAward,
        CompetitionEvent,
        CompetitionParticipant,
    )
    from apps.contributions.models import Contribution, MemberRanking, RankingObjection
    from apps.dashboard.portal_models import PortalPublication, PortalSettings
    from apps.exports.custom_report_models import CustomReport
    from apps.exports.scheduled_report_models import (
        ScheduledReport,
        ScheduledReportExecution,
    )
    from apps.files.models import FileAsset, FileVersion
    from apps.finance.models import (
        FinanceBudget,
        FinanceExpense,
        FinanceIncome,
        FinanceReceipt,
    )
    from apps.imports.models import ImportTask
    from apps.intellectual_property.models import (
        IPApplicationContributor,
        IPMaterialVersion,
        IPObjection,
        IPReturnRecord,
        IntellectualPropertyApplication,
    )
    from apps.members.models import FlexibleWorkSchedule, MemberSkill
    from apps.notifications.models import Announcement, Notification
    from apps.projects.models import (
        ProjectMember,
        ProjectMembershipEvent,
        ProjectStageLog,
    )
    from apps.sensitive.models import SensitiveAccessRequest, SensitiveData
    from apps.tasks.models import Task
    from apps.users.models import UserLifecycleEvent, UserPreference

    demo_users = _demo_users()
    demo_projects = _demo_projects()
    project_ids = list(demo_projects.values_list('id', flat=True))
    demo_competitions = Competition.objects.filter(
        project_id__in=project_ids,
    )
    demo_competition_events = CompetitionEvent.objects.filter(
        entries__in=demo_competitions,
    ).distinct()
    demo_competition_awards = CompetitionAward.objects.filter(
        competition__in=demo_competitions,
    )
    demo_reports = CustomReport.objects.filter(
        created_by__in=demo_users,
        name__startswith=DEMO_MARKER,
    )
    demo_schedules = ScheduledReport.objects.filter(report__in=demo_reports)
    schedule_recipient_through = ScheduledReport.recipients.through
    demo_teams = Team.objects.filter(code=DEMO_TEAM_CODE)
    demo_ip = IntellectualPropertyApplication.objects.filter(
        Q(related_project_id__in=project_ids)
        | Q(application_code__startswith='IP-TEAM-DEMO-')
    ).distinct()
    demo_publications = PortalPublication.objects.filter(
        Q(
            content_type=PortalPublication.ContentType.PROJECT,
            object_id__in=project_ids,
        )
        | Q(
            content_type=PortalPublication.ContentType.IP_APPLICATION,
            object_id__in=demo_ip.values_list('id', flat=True),
        )
        | Q(
            content_type=PortalPublication.ContentType.MEMBER,
            object_id__in=demo_users.values_list('id', flat=True),
        )
    )
    demo_sensitive_data = SensitiveData.objects.filter(
        project_id__in=project_ids,
        title__startswith=DEMO_MARKER,
    )
    demo_notifications = Notification.objects.filter(
        title__startswith=DEMO_MARKER,
    )
    demo_imports = ImportTask.objects.filter(
        created_by__in=demo_users,
        file_path__contains='seed_demo_data',
    )
    task_attachment_through = Task.attachment_files.through
    task_collaborator_through = Task.collaborators.through
    payload = {
        'schema': 'team-management-demo-v2',
        'generated_at': timezone.now().isoformat(),
        'users': list(
            demo_users.values(
                'email', 'name', 'global_role', 'grade', 'major', 'is_active',
                'avatar',
                'membership_status', 'team_joined_at', 'team_left_at',
                'exit_reason', 'handover_to__email', 'handover_notes',
            )
        ),
        'preferences': list(
            UserPreference.objects.filter(user__in=demo_users).values(
                'user__email', 'theme_color', 'primary_color', 'default_landing',
                'sidebar_collapsed', 'notification_sound', 'items_per_page',
                'dashboard_layout', 'default_scope', 'sidebar_order',
                'favorite_routes', 'saved_filters', 'notification_preferences',
            )
        ),
        'member_skills': list(
            MemberSkill.objects.filter(user__in=demo_users).values(
                'user__email', 'skill__name', 'proficiency', 'created_at',
            )
        ),
        'flexible_work_schedules': list(
            FlexibleWorkSchedule.objects.filter(
                user__in=demo_users,
                notes__startswith=DEMO_MARKER,
            ).values(
                'user__email', 'period_start', 'period_end', 'work_hours',
                'detail', 'can_offline', 'can_urgent', 'is_saturated',
                'notes', 'filled_at',
            )
        ),
        'projects': list(
            demo_projects.values(
                'code', 'name', 'status', 'priority', 'current_stage',
                'leader__email', 'start_date', 'planned_end_date',
                'actual_end_date', 'intro', 'last_leader_update',
                'archived_at', 'created_at',
            )
        ),
        'project_members': list(
            ProjectMember.objects.filter(project_id__in=project_ids).values(
                'project__code', 'user__email', 'role_in_project', 'status',
                'joined_at', 'exited_at', 'exit_reason',
                'handover_to__user__email', 'handover_notes',
            )
        ),
        'project_membership_events': list(
            ProjectMembershipEvent.objects.filter(
                membership__project_id__in=project_ids,
            ).values(
                'membership__project__code', 'membership__user__email',
                'event_type', 'from_role', 'to_role', 'from_status',
                'to_status', 'reason', 'handover_to__user__email',
                'handover_notes', 'operator__email', 'created_at',
            )
        ),
        'project_stage_logs': list(
            ProjectStageLog.objects.filter(project_id__in=project_ids).values(
                'project__code', 'from_stage', 'to_stage', 'operator__email',
                'note', 'created_at',
            )
        ),
        'user_lifecycle_events': list(
            UserLifecycleEvent.objects.filter(user__in=demo_users).values(
                'user__email', 'event_type', 'from_status', 'to_status',
                'from_role', 'to_role', 'reason', 'handover_to__email',
                'handover_notes', 'operator__email', 'created_at',
            )
        ),
        'teams': list(
            demo_teams.values(
                'code', 'name', 'description', 'logo', 'contact_email',
                'join_message', 'is_active', 'owner__email', 'created_at',
            )
        ),
        'team_members': list(
            TeamMember.objects.filter(team__in=demo_teams).values(
                'team__code', 'user__email', 'role', 'status', 'joined_at',
                'left_at', 'exit_reason', 'handover_to__user__email',
                'handover_notes',
            )
        ),
        'team_membership_events': list(
            TeamMembershipEvent.objects.filter(
                membership__team__in=demo_teams,
            ).values(
                'membership__team__code', 'membership__user__email',
                'event_type', 'from_role', 'to_role', 'from_status',
                'to_status', 'reason', 'handover_to__user__email',
                'handover_notes', 'operator__email', 'created_at',
            )
        ),
        'competition_events': list(
            demo_competition_events.values(
                'organization__code', 'name', 'edition', 'organizer',
                'created_at', 'updated_at',
            )
        ),
        'competitions': list(
            demo_competitions.values(
                'project__code',
                'event__organization__code', 'event__name',
                'event__edition', 'event__organizer', 'entry_name',
                'name', 'comp_type', 'level', 'organizer',
                'register_date', 'material_deadline', 'review_date',
                'defense_date', 'school_date', 'city_date', 'province_date',
                'national_date', 'result_date', 'status', 'current_stage',
                'is_promoted', 'is_awarded', 'award_level',
                'not_promoted_reason', 'improvement_suggestion',
                'review_summary', 'created_at', 'updated_at',
            )
        ),
        'competition_participants': list(
            CompetitionParticipant.objects.filter(
                competition__in=demo_competitions,
            ).values(
                'competition__project__code',
                'competition__event__organization__code',
                'competition__event__name',
                'competition__event__edition',
                'competition__event__organizer',
                'competition__entry_name', 'competition__name',
                'competition__register_date',
                'user__email', 'role', 'participation_status',
                'responsibility', 'joined_at', 'updated_at',
            )
        ),
        'competition_awards': list(
            demo_competition_awards.values(
                'competition__project__code',
                'competition__event__organization__code',
                'competition__event__name',
                'competition__event__edition',
                'competition__event__organizer',
                'competition__entry_name', 'competition__name',
                'competition__register_date',
                'award_name', 'award_level', 'award_date', 'notes',
                'created_at', 'updated_at',
            )
        ),
        'competition_award_recipients': [
            {
                'competition__project__code': award.competition.project.code,
                'competition__event__organization__code': (
                    award.competition.event.organization.code
                    if (
                        award.competition.event_id
                        and award.competition.event.organization_id
                    )
                    else None
                ),
                'competition__event__name': (
                    award.competition.event.name
                    if award.competition.event_id
                    else None
                ),
                'competition__event__edition': (
                    award.competition.event.edition
                    if award.competition.event_id
                    else None
                ),
                'competition__event__organizer': (
                    award.competition.event.organizer
                    if award.competition.event_id
                    else None
                ),
                'competition__entry_name': award.competition.entry_name,
                'competition__name': award.competition.name,
                'competition__register_date': award.competition.register_date,
                'award_name': award.award_name,
                'award_level': award.award_level,
                'award_date': award.award_date,
                'recipient__email': recipient_email,
            }
            for award in demo_competition_awards.select_related(
                'competition__project',
                'competition__event__organization',
            ).prefetch_related('recipients')
            for recipient_email in award.recipients.values_list(
                'email',
                flat=True,
            )
        ],
        'tasks': list(
            Task.objects.filter(project_id__in=project_ids).values(
                'project__code', 'title', 'description', 'status', 'priority',
                'assignee__email', 'creator__email', 'reviewer__email',
                'start_date', 'deadline', 'completed_at', 'delay_reason',
                'completion_note',
            )
        ),
        'finance_budgets': list(
            FinanceBudget.objects.filter(project_id__in=project_ids).values(
                'project__code', 'bonus_amount', 'other_income',
                'used_amount', 'pending_reimbursement', 'status', 'period',
            )
        ),
        'finance_expenses': list(
            FinanceExpense.objects.filter(project_id__in=project_ids).values(
                'project__code',
                'competition_entry__project__code',
                'competition_entry__event__organization__code',
                'competition_entry__event__name',
                'competition_entry__event__edition',
                'competition_entry__event__organizer',
                'competition_entry__entry_name',
                'competition_entry__name',
                'competition_entry__register_date',
                'title', 'amount', 'expense_date',
                'category', 'spender__email', 'reimbursement_status',
                'purpose', 'reviewer__email', 'review_opinion', 'reviewed_at',
                'applied_by__email', 'applied_at', 'paid_by__email', 'paid_at',
                'payment_method', 'payment_reference',
            )
        ),
        'finance_incomes': list(
            FinanceIncome.objects.filter(project_id__in=project_ids).values(
                'project__code',
                'competition_entry__project__code',
                'competition_entry__event__organization__code',
                'competition_entry__event__name',
                'competition_entry__event__edition',
                'competition_entry__event__organizer',
                'competition_entry__entry_name',
                'competition_entry__name',
                'competition_entry__register_date',
                'title', 'amount', 'income_type',
                'income_date', 'source', 'reference_number', 'note',
                'recorded_by__email',
            )
        ),
        'finance_receipts': list(
            FinanceReceipt.objects.filter(
                expense__project_id__in=project_ids,
            ).values(
                'expense__project__code', 'expense__title', 'file',
                'expense__expense_date', 'expense__amount',
                'uploaded_by__email', 'created_at',
            )
        ),
        'files': list(
            FileAsset.objects.filter(project_id__in=project_ids).values(
                'project__code', 'team__code',
                'competition_entry__project__code',
                'competition_entry__event__organization__code',
                'competition_entry__event__name',
                'competition_entry__event__edition',
                'competition_entry__event__organizer',
                'competition_entry__entry_name',
                'competition_entry__name',
                'competition_entry__register_date',
                'name', 'file', 'level', 'size',
                'content_type', 'uploader__email', 'version', 'file_hash',
                'watermark_text', 'created_at',
            )
        ),
        'file_versions': list(
            FileVersion.objects.filter(
                file_asset__project_id__in=project_ids,
            ).values(
                'file_asset__project__code',
                'file_asset__competition_entry__project__code',
                'file_asset__competition_entry__event__organization__code',
                'file_asset__competition_entry__event__name',
                'file_asset__competition_entry__event__edition',
                'file_asset__competition_entry__event__organizer',
                'file_asset__competition_entry__entry_name',
                'file_asset__competition_entry__name',
                'file_asset__competition_entry__register_date',
                'file_asset__name', 'version',
                'file', 'uploader__email', 'created_at',
            )
        ),
        'task_attachments': list(
            task_attachment_through.objects.filter(
                task__project_id__in=project_ids,
            ).values(
                'task__project__code', 'task__title',
                'fileasset__name',
            )
        ),
        'task_collaborators': list(
            task_collaborator_through.objects.filter(
                task__project_id__in=project_ids,
            ).values(
                'task__project__code', 'task__title', 'user__email',
            )
        ),
        'sensitive_data': list(
            demo_sensitive_data.values(
                'data_type', 'title', 'display_name', 'key_version',
                'file_attachment__name', 'project__code', 'uploader__email',
                'is_encrypted', 'created_at', 'updated_at',
            )
        ),
        'sensitive_access_requests': list(
            SensitiveAccessRequest.objects.filter(
                sensitive_data__in=demo_sensitive_data,
            ).values(
                'sensitive_data__title', 'applicant__email', 'project__code',
                'reason', 'usage_scenario', 'expected_use_time', 'request_note',
                'is_download', 'status', 'approver__email', 'approval_comment',
                'approval_opinion', 'approved_at', 'access_expires_at',
                'viewed_at', 'created_at',
            )
        ),
        'contributions': list(
            Contribution.objects.filter(project_id__in=project_ids).values(
                'project__code', 'user__email', 'contribution_type',
                'description', 'content', 'score', 'weight', 'status',
                'related_object_id', 'period', 'proof_file__name',
                'filled_by__email', 'reviewer__email', 'reviewed_at',
                'review_opinion', 'created_at',
            )
        ),
        'member_rankings': list(
            MemberRanking.objects.filter(project_id__in=project_ids).values(
                'project__code', 'user__email', 'period', 'status',
                'total_score', 'rank', 'task_completed_count',
                'project_count', 'competition_count',
                'ip_contribution_count', 'is_published', 'is_public',
                'rule_version', 'rule_snapshot', 'score_snapshot',
                'confirmed_at', 'confirmed_by__email', 'generated_at',
            )
        ),
        'ranking_objections': list(
            RankingObjection.objects.filter(
                ranking__project_id__in=project_ids,
            ).values(
                'ranking__project__code', 'ranking__user__email',
                'ranking__period', 'objector__email', 'content', 'status',
                'reply', 'leader_opinion', 'leader_reviewer__email',
                'leader_reviewed_at', 'teacher_opinion',
                'teacher_confirmer__email', 'teacher_confirmed_at',
                'final_result', 'original_rank', 'corrected_rank',
                'original_total_score', 'corrected_total_score',
                'adjustment_snapshot', 'adjustment_applied_at',
                'adjustment_applied_by__email', 'handler__email',
                'created_at',
            )
        ),
        'custom_reports': list(
            demo_reports.values(
                'name', 'description', 'report_type', 'config',
                'created_by__email', 'is_scheduled',
            )
        ),
        'scheduled_reports': list(
            demo_schedules.values(
                'report__name', 'created_by__email', 'frequency',
                'execution_time', 'weekday', 'day_of_month', 'timezone',
                'file_format', 'last_run', 'next_run', 'last_status',
                'last_error', 'is_active',
            )
        ),
        'scheduled_report_recipients': list(
            schedule_recipient_through.objects.filter(
                scheduledreport__in=demo_schedules,
            ).values(
                'scheduledreport__report__name', 'user__email',
            )
        ),
        'scheduled_report_executions': list(
            ScheduledReportExecution.objects.filter(
                schedule__in=demo_schedules,
            ).values(
                'schedule__report__name', 'trigger', 'status', 'file',
                'file_name', 'file_format', 'file_size', 'delivery_status',
                'recipient_snapshot', 'message', 'error', 'started_at',
                'finished_at', 'generated_by__email',
            )
        ),
        'notifications': list(
            demo_notifications.values(
                'notification_type', 'channel', 'email_delivery_status',
                'email_digest_frequency', 'email_attempted_at',
                'email_sent_at', 'email_delivery_error', 'title', 'content', 'priority',
                'recipient__email', 'sender__email', 'is_read', 'read_at',
                'related_object_type', 'related_object_id', 'created_at',
            )
        ),
        'announcements': list(
            Announcement.objects.filter(
                author__in=demo_users,
                title__startswith=DEMO_MARKER,
            ).values(
                'title', 'content', 'category', 'status', 'is_pinned',
                'is_public', 'author__email', 'published_at',
                'created_at', 'updated_at',
            )
        ),
        'operation_logs': list(
            OperationLog.objects.filter(
                description__startswith=DEMO_MARKER,
            ).values(
                'operator__email', 'operation_type', 'module', 'object_type',
                'object_id', 'description', 'request_method', 'request_path',
                'request_ip', 'user_agent', 'request_data', 'response_status',
                'is_success', 'error_message', 'created_at',
            )
        ),
        'imports': list(
            demo_imports.values(
                'module', 'file_path', 'status', 'total_rows', 'valid_rows',
                'error_rows', 'field_mapping', 'preview_data', 'snapshot',
                'error_details', 'created_by__email', 'created_at',
            )
        ),
        'ip_applications': list(
            demo_ip.values(
                'application_code', 'title', 'ip_type', 'related_project__code',
                'status', 'main_writer__email', 'applicant_executor__email',
                'material_manager__email', 'project_reviewer__email',
                'teacher_confirmer__email', 'start_date', 'submit_date',
                'accepted_date', 'authorized_date', 'return_count',
                'current_problem', 'final_certificate_file__name', 'intro',
                'created_by__email', 'created_at',
            )
        ),
        'ip_contributors': list(
            IPApplicationContributor.objects.filter(
                application__in=demo_ip,
            ).values(
                'application__application_code', 'user__email', 'role',
                'contribution_description', 'responsibility_description',
                'is_confirmed', 'confirmed_by__email', 'confirmed_at',
            )
        ),
        'ip_material_versions': list(
            IPMaterialVersion.objects.filter(application__in=demo_ip).values(
                'application__application_code', 'file_asset__name',
                'material_type', 'version', 'uploaded_by__email',
                'change_note', 'is_final', 'created_at',
            )
        ),
        'ip_return_records': list(
            IPReturnRecord.objects.filter(application__in=demo_ip).values(
                'application__application_code', 'return_time',
                'return_source', 'return_reason', 'responsibility_type',
                'responsible_user__email', 'assigned_by__email',
                'modify_deadline', 'actual_modifier__email',
                'modify_description', 'result', 'proof_file__name',
                'created_at',
            )
        ),
        'ip_objections': list(
            IPObjection.objects.filter(application__in=demo_ip).values(
                'application__application_code', 'objector__email',
                'objection_type', 'content', 'status',
                'leader_opinion', 'leader_reviewer__email',
                'leader_reviewed_at', 'teacher_opinion',
                'teacher_confirmer__email', 'teacher_confirmed_at',
                'final_result', 'created_at',
            )
        ),
        'portal_settings': list(
            PortalSettings.objects.filter(updated_by__in=demo_users).values(
                'singleton_key', 'team_name', 'tagline', 'summary',
                'about_title', 'about_text', 'logo_url', 'hero_image_url',
                'story_image_url', 'contact_email', 'join_title',
                'join_message', 'join_url', 'updated_by__email', 'updated_at',
            )
        ),
        'portal_publications': list(
            demo_publications.values(
                'content_type', 'object_id', 'is_public', 'is_featured',
                'member_consent', 'display_order', 'custom_title',
                'custom_summary', 'image_url', 'updated_by__email',
                'created_at', 'updated_at',
            )
        ),
    }

    from apps.projects.models import Project
    from apps.users.models import User

    project_keys = dict(
        Project.all_objects.filter(id__in=project_ids).values_list('id', 'code')
    )
    user_keys = dict(demo_users.values_list('id', 'email'))
    ip_keys = dict(demo_ip.values_list('id', 'application_code'))
    for publication in payload['portal_publications']:
        object_id = publication.get('object_id')
        publication['object_key'] = {
            PortalPublication.ContentType.PROJECT: project_keys,
            PortalPublication.ContentType.IP_APPLICATION: ip_keys,
            PortalPublication.ContentType.MEMBER: user_keys,
        }.get(publication.get('content_type'), {}).get(object_id, '')

    related_models = {
        'project': ('projects.Project', lambda obj: {'code': obj.code}),
        'task': (
            'tasks.Task',
            lambda obj: {'project': obj.project.code, 'title': obj.title},
        ),
        'competition': (
            'competitions.Competition',
            lambda obj: {
                'project': obj.project.code,
                'name': obj.name,
                'register_date': (
                    obj.register_date.isoformat()
                    if obj.register_date
                    else None
                ),
                'event_organization': (
                    obj.event.organization.code
                    if obj.event_id and obj.event.organization_id
                    else None
                ),
                'event_name': obj.event.name if obj.event_id else None,
                'event_edition': (
                    obj.event.edition if obj.event_id else None
                ),
                'event_organizer': (
                    obj.event.organizer if obj.event_id else None
                ),
                'entry_name': obj.entry_name,
            },
        ),
        'finance_expense': (
            'finance.FinanceExpense',
            lambda obj: {
                'project': obj.project.code,
                'title': obj.title,
                'expense_date': obj.expense_date.isoformat(),
                'amount': str(obj.amount),
            },
        ),
        'contribution': (
            'contributions.Contribution',
            lambda obj: {
                'project': obj.project.code if obj.project_id else '',
                'user': obj.user.email,
                'period': obj.period,
                'type': obj.contribution_type,
            },
        ),
        'ip_application': (
            'intellectual_property.IntellectualPropertyApplication',
            lambda obj: {'application_code': obj.application_code},
        ),
        'sensitive_request': (
            'sensitive.SensitiveAccessRequest',
            lambda obj: {
                'title': obj.sensitive_data.title,
                'applicant': obj.applicant.email,
                'is_download': obj.is_download,
            },
        ),
        'ranking_objection': (
            'contributions.RankingObjection',
            lambda obj: {
                'project': obj.ranking.project.code,
                'user': obj.ranking.user.email,
                'period': obj.ranking.period,
                'objector': obj.objector.email,
            },
        ),
        'work_schedule': (
            'members.FlexibleWorkSchedule',
            lambda obj: {
                'user': obj.user.email,
                'period_start': obj.period_start.isoformat(),
            },
        ),
    }
    from django.apps import apps

    for notification in payload['notifications']:
        notification['related_object_key'] = None
        descriptor = related_models.get(notification.get('related_object_type'))
        object_id = notification.get('related_object_id')
        if not descriptor or not object_id:
            continue
        model_label, key_builder = descriptor
        try:
            related_object = apps.get_model(model_label)._base_manager.get(pk=object_id)
        except apps.get_model(model_label).DoesNotExist:
            continue
        notification['related_object_key'] = key_builder(related_object)

    return payload


def create_demo_backup(*, created_by=None, reason='manual') -> dict:
    """创建包含清单、业务快照及演示附件的 ZIP 包。"""
    from apps.common.team_models import Team
    from apps.exports.scheduled_report_models import ScheduledReportExecution
    from apps.files.models import FileAsset, FileVersion
    from apps.finance.models import FinanceReceipt
    from apps.imports.models import ImportTask

    now = timezone.localtime()
    prefix = now.strftime('demo-%Y%m%d-%H%M%S')
    backup_id = prefix
    suffix = 1
    while _safe_backup_path(backup_id).exists():
        backup_id = f'{prefix}-{suffix:03d}'
        suffix += 1
    target = _safe_backup_path(backup_id)

    snapshot_content = json.dumps(
        _snapshot_payload(),
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode('utf-8')
    entries = [
        {
            'path': 'data/demo_snapshot.json',
            'size': len(snapshot_content),
            'sha256': _sha256_bytes(snapshot_content),
        }
    ]
    project_ids = list(_demo_projects().values_list('id', flat=True))
    assets = list(FileAsset.objects.filter(project_id__in=project_ids))
    versions = list(FileVersion.objects.filter(file_asset__project_id__in=project_ids))
    receipts = list(FinanceReceipt.objects.filter(expense__project_id__in=project_ids))
    demo_users = _demo_users()
    demo_teams = Team.objects.filter(code=DEMO_TEAM_CODE)
    demo_imports = list(
        ImportTask.objects.filter(
            created_by__in=demo_users,
            file_path__contains='seed_demo_data',
        ).exclude(file_path='')
    )
    report_executions = list(
        ScheduledReportExecution.objects.filter(
            schedule__report__created_by__in=demo_users,
            schedule__report__name__startswith=DEMO_MARKER,
        ).exclude(file='')
    )

    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=backup_root(),
            suffix='.tmp',
            delete=False,
        ) as temp:
            temp_name = Path(temp.name)
        with zipfile.ZipFile(temp_name, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('data/demo_snapshot.json', snapshot_content)
            used_paths = set()
            for model_name, records, file_attribute in (
                ('assets', assets, 'file'),
                ('versions', versions, 'file'),
                ('receipts', receipts, 'file'),
                ('scheduled_reports', report_executions, 'file'),
                ('avatars', list(demo_users.exclude(avatar='')), 'avatar'),
                ('team_logos', list(demo_teams.exclude(logo='')), 'logo'),
            ):
                for record in records:
                    file_field = getattr(record, file_attribute)
                    if not file_field:
                        continue
                    try:
                        file_field.open('rb')
                        content = file_field.read()
                    except (FileNotFoundError, OSError):
                        continue
                    finally:
                        try:
                            file_field.close()
                        except Exception:
                            pass
                    original_name = Path(file_field.name).name
                    archive_path = f'media/{model_name}/{record.pk}_{original_name}'
                    if archive_path in used_paths:
                        continue
                    used_paths.add(archive_path)
                    archive.writestr(archive_path, content)
                    entries.append({
                        'path': archive_path,
                        'size': len(content),
                        'sha256': _sha256_bytes(content),
                        'kind': model_name,
                        'storage_name': file_field.name,
                    })

            allowed_import_roots = (
                Path(settings.MEDIA_ROOT).resolve(),
                (Path(settings.BASE_DIR) / 'seed_assets').resolve(),
            )
            for import_task in demo_imports:
                import_path = Path(import_task.file_path).resolve()
                if (
                    not import_path.is_file()
                    or not any(
                        import_path.is_relative_to(root)
                        for root in allowed_import_roots
                    )
                ):
                    continue
                content = import_path.read_bytes()
                archive_path = f'media/imports/{import_task.pk}_{import_path.name}'
                if archive_path in used_paths:
                    continue
                used_paths.add(archive_path)
                archive.writestr(archive_path, content)
                media_root = Path(settings.MEDIA_ROOT).resolve()
                storage_name = (
                    import_path.relative_to(media_root).as_posix()
                    if import_path.is_relative_to(media_root)
                    else ''
                )
                entries.append({
                    'path': archive_path,
                    'size': len(content),
                    'sha256': _sha256_bytes(content),
                    'kind': 'imports',
                    'storage_name': storage_name,
                })

            manifest = {
                'schema': 'team-management-demo-backup-v2',
                'backup_id': backup_id,
                'created_at': timezone.now().isoformat(),
                'created_by': getattr(created_by, 'email', ''),
                'reason': reason,
                'restore_strategy': 'snapshot_overlay_v2',
                'restore_command': 'seed_demo_data --clean --force + snapshot overlay',
                'requires_relogin': True,
                'entry_count': len(entries),
                'entries': entries,
            }
            archive.writestr(
                'manifest.json',
                json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'),
            )
            archive.writestr(
                'README.txt',
                (
                    '团队管理平台演示数据备份包\n'
                    '该包用于恢复内置演示环境，不是生产数据库备份。\n'
                    '恢复会先校验包内文件，再重建完整演示基线，并按该包的业务快照'
                    '和实际附件覆盖到备份时状态；完成后需重新登录。\n'
                ).encode('utf-8'),
            )
        os.replace(temp_name, target)
    finally:
        if temp_name and temp_name.exists():
            temp_name.unlink()

    return describe_backup(target)


def _read_manifest(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path, 'r') as archive:
            return json.loads(archive.read('manifest.json').decode('utf-8'))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        raise DemoBackupError('备份包已损坏或缺少清单') from exc


def describe_backup(path: Path) -> dict:
    manifest = _read_manifest(path)
    stat = path.stat()
    return {
        'backup_id': manifest.get('backup_id', path.stem),
        'created_at': manifest.get('created_at'),
        'created_by': manifest.get('created_by', ''),
        'reason': manifest.get('reason', ''),
        'status': 'ready',
        'size': stat.st_size,
        'entry_count': manifest.get('entry_count', 0),
        'sha256': _sha256_file(path),
        'download_url': f'/common/backup/{path.stem}/download/',
        'requires_relogin': bool(manifest.get('requires_relogin', True)),
    }


def list_demo_backups() -> list[dict]:
    backups = []
    for path in backup_root().glob('demo-*.zip'):
        try:
            backups.append(describe_backup(path))
        except DemoBackupError:
            backups.append({
                'backup_id': path.stem,
                'created_at': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                'status': 'corrupt',
                'size': path.stat().st_size,
            })
    return sorted(backups, key=lambda item: item.get('created_at') or '', reverse=True)


def _verify_backup_path(path: Path) -> dict:
    manifest = _read_manifest(path)
    if manifest.get('schema') not in SUPPORTED_BACKUP_SCHEMAS:
        raise DemoBackupError('备份包版本不受支持')
    entries = manifest.get('entries')
    if not isinstance(entries, list) or not entries:
        raise DemoBackupError('备份包清单缺少文件条目')
    with zipfile.ZipFile(path, 'r') as archive:
        archive_names = archive.namelist()
        if len(set(archive_names)) != len(archive_names):
            raise DemoBackupError('备份包包含重复文件路径')
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
                raise DemoBackupError('备份包清单包含无效文件条目')
            try:
                content = archive.read(entry['path'])
            except KeyError as exc:
                raise DemoBackupError(f'备份包缺少文件：{entry["path"]}') from exc
            if len(content) != entry.get('size') or _sha256_bytes(content) != entry.get('sha256'):
                raise DemoBackupError(f'备份文件校验失败：{entry["path"]}')
    return manifest


def verify_demo_backup(backup_id: str) -> dict:
    path = _safe_backup_path(backup_id)
    if not path.exists():
        raise DemoBackupError('备份包不存在')
    return _verify_backup_path(path)


def import_demo_backup(uploaded_file) -> dict:
    """校验并导入此前下载的演示 ZIP，不覆盖同编号的不同内容。"""
    if not uploaded_file:
        raise DemoBackupError('请选择演示备份 ZIP 文件')
    size = getattr(uploaded_file, 'size', 0)
    if size <= 0:
        raise DemoBackupError('上传的备份包为空')
    if size > MAX_DEMO_BACKUP_SIZE:
        raise DemoBackupError('演示备份包不能超过 512MB')
    if Path(getattr(uploaded_file, 'name', '')).suffix.lower() != '.zip':
        raise DemoBackupError('仅支持 ZIP 格式的演示备份包')

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=backup_root(),
            suffix='.upload.tmp',
            delete=False,
        ) as temp:
            temp_path = Path(temp.name)
            chunks = (
                uploaded_file.chunks()
                if hasattr(uploaded_file, 'chunks')
                else iter(lambda: uploaded_file.read(1024 * 1024), b'')
            )
            written = 0
            for chunk in chunks:
                written += len(chunk)
                if written > MAX_DEMO_BACKUP_SIZE:
                    raise DemoBackupError('演示备份包不能超过 512MB')
                temp.write(chunk)

        manifest = _verify_backup_path(temp_path)
        backup_id = manifest.get('backup_id', '')
        target = _safe_backup_path(backup_id)
        if target.exists():
            if _sha256_file(target) == _sha256_file(temp_path):
                return describe_backup(target)
            raise DemoBackupError('服务器已存在同编号但内容不同的备份包')
        os.replace(temp_path, target)
        temp_path = None
        return describe_backup(target)
    except (zipfile.BadZipFile, OSError) as exc:
        raise DemoBackupError('上传的备份包无效或无法保存') from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _read_snapshot(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path, 'r') as archive:
            snapshot = json.loads(
                archive.read('data/demo_snapshot.json').decode('utf-8')
            )
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        raise DemoBackupError('备份包缺少可恢复的业务快照') from exc
    if snapshot.get('schema') not in {
        'team-management-demo-v1',
        'team-management-demo-v2',
    }:
        raise DemoBackupError('业务快照版本不受支持')
    return snapshot


def _row_defaults(model, row: dict, *, exclude=()) -> dict:
    excluded = set(exclude)
    defaults = {}
    for field in model._meta.concrete_fields:
        if (
            field.primary_key
            or field.is_relation
            or field.name in excluded
            or field.name not in row
        ):
            continue
        value = row[field.name]
        defaults[field.name] = (
            field.to_python(value) if value is not None else None
        )
    return defaults


def _upsert_snapshot_row(
    model,
    lookup: dict,
    row: dict,
    *,
    relations=None,
    exclude=(),
    stats=None,
):
    defaults = _row_defaults(model, row, exclude=exclude)
    for field_name, related_id in (relations or {}).items():
        defaults[f'{field_name}_id'] = related_id
    for lookup_name in lookup:
        defaults.pop(lookup_name, None)
    obj, created = model._base_manager.update_or_create(
        defaults=defaults,
        **lookup,
    )

    # auto_now/auto_now_add 会覆盖导入值；随后用 queryset.update 精确还原。
    timestamps = {}
    for field_name in (
        'created_at',
        'updated_at',
        'filled_at',
        'started_at',
        'joined_at',
    ):
        if field_name in row and row[field_name] is not None:
            field = model._meta.get_field(field_name)
            timestamps[field_name] = field.to_python(row[field_name])
    if timestamps:
        model._base_manager.filter(pk=obj.pk).update(**timestamps)
        for field_name, value in timestamps.items():
            setattr(obj, field_name, value)
    if stats is not None:
        stats['created' if created else 'updated'] += 1
    return obj


def _delete_missing(queryset, desired_keys: set, key_builder, stats, file_fields=()):
    stale_ids = []
    for obj in queryset.iterator():
        if key_builder(obj) in desired_keys:
            continue
        for field_name in file_fields:
            file_field = getattr(obj, field_name, None)
            if file_field:
                try:
                    file_field.delete(save=False)
                except (FileNotFoundError, OSError):
                    pass
        stale_ids.append(obj.pk)
    if stale_ids:
        deleted, _ = queryset.model._base_manager.filter(pk__in=stale_ids).delete()
        stats['deleted'] += deleted


def _required_id(model, lookup: dict, description: str):
    value = model._base_manager.filter(**lookup).values_list('pk', flat=True).first()
    if value is None:
        raise DemoBackupError(f'快照引用不存在：{description}')
    return value


def _optional_id(model, lookup: dict):
    if not all(value not in (None, '') for value in lookup.values()):
        return None
    return model._base_manager.filter(**lookup).values_list('pk', flat=True).first()


def _competition_snapshot_key(row: dict, *, prefix='') -> tuple:
    """Return a stable competition natural key for new and legacy snapshots."""
    project_code = row.get(f'{prefix}project__code')
    event_name = row.get(f'{prefix}event__name')
    event_edition = row.get(f'{prefix}event__edition')
    if event_name not in (None, '') and event_edition not in (None, ''):
        return (
            'event',
            project_code,
            row.get(f'{prefix}event__organization__code') or '',
            event_name,
            str(event_edition),
            row.get(f'{prefix}event__organizer') or '',
            row.get(f'{prefix}entry_name') or '',
        )
    return (
        'legacy',
        project_code,
        row.get(f'{prefix}name') or '',
        str(row.get(f'{prefix}register_date') or ''),
    )


def _competition_object_key(competition, *, use_event_key: bool) -> tuple:
    if use_event_key and competition.event_id:
        return (
            'event',
            competition.project.code,
            (
                competition.event.organization.code
                if competition.event.organization_id
                else ''
            ),
            competition.event.name,
            str(competition.event.edition),
            competition.event.organizer or '',
            competition.entry_name or '',
        )
    return (
        'legacy',
        competition.project.code,
        competition.name or '',
        str(competition.register_date or ''),
    )


def _competition_lookup_from_row(
    row: dict,
    *,
    prefix,
    project_model,
    event_model,
) -> dict:
    project_code = row.get(f'{prefix}project__code')
    project_id = _required_id(
        project_model,
        {'code': project_code},
        project_code,
    )
    event_name = row.get(f'{prefix}event__name')
    event_edition = row.get(f'{prefix}event__edition')
    if event_name not in (None, '') and event_edition not in (None, ''):
        event_lookup = {
            'name': event_name,
            'edition': str(event_edition),
            'organizer': row.get(f'{prefix}event__organizer') or '',
        }
        organization_code = row.get(
            f'{prefix}event__organization__code'
        )
        if organization_code:
            event_lookup['organization__code'] = organization_code
        else:
            event_lookup['organization__isnull'] = True
        event_id = _required_id(
            event_model,
            event_lookup,
            f'{event_name} {event_edition}',
        )
        return {
            'project_id': project_id,
            'event_id': event_id,
            'entry_name': row.get(f'{prefix}entry_name') or '',
        }

    lookup = {
        'project_id': project_id,
        'name': row.get(f'{prefix}name') or '',
    }
    if row.get(f'{prefix}register_date') not in (None, ''):
        lookup['register_date'] = row[f'{prefix}register_date']
    return lookup


def _competition_id_from_row(
    row: dict,
    *,
    prefix,
    competition_model,
    project_model,
    event_model,
):
    lookup = _competition_lookup_from_row(
        row,
        prefix=prefix,
        project_model=project_model,
        event_model=event_model,
    )
    return _required_id(
        competition_model,
        lookup,
        str(_competition_snapshot_key(row, prefix=prefix)),
    )


def _replace_history_rows(model, queryset, rows, relation_builder, stats):
    deleted, _ = queryset.delete()
    stats['deleted'] += deleted
    for row in rows:
        relations = relation_builder(row)
        defaults = _row_defaults(model, row)
        defaults.update({f'{name}_id': value for name, value in relations.items()})
        obj = model._base_manager.create(**defaults)
        timestamp_updates = {}
        for field_name in ('created_at', 'updated_at'):
            if field_name in row and row[field_name] is not None:
                field = model._meta.get_field(field_name)
                timestamp_updates[field_name] = field.to_python(row[field_name])
        if timestamp_updates:
            model._base_manager.filter(pk=obj.pk).update(**timestamp_updates)
        stats['created'] += 1


def _restore_snapshot_overlay(snapshot: dict) -> dict:
    """在完整种子基线上同步包内快照，稳定标识缺失时立即失败。"""
    from apps.audit.models import OperationLog
    from apps.common.team_models import Team, TeamMember, TeamMembershipEvent
    from apps.competitions.models import (
        Competition,
        CompetitionAward,
        CompetitionEvent,
        CompetitionParticipant,
    )
    from apps.contributions.models import Contribution, MemberRanking, RankingObjection
    from apps.dashboard.portal_models import PortalPublication, PortalSettings
    from apps.exports.custom_report_models import CustomReport
    from apps.exports.scheduled_report_models import ScheduledReport, ScheduledReportExecution
    from apps.files.models import FileAsset, FileVersion
    from apps.finance.models import FinanceBudget, FinanceExpense, FinanceIncome, FinanceReceipt
    from apps.imports.models import ImportTask
    from apps.intellectual_property.models import (
        IPApplicationContributor,
        IPMaterialVersion,
        IPObjection,
        IPReturnRecord,
        IntellectualPropertyApplication,
    )
    from apps.members.models import FlexibleWorkSchedule, MemberSkill, SkillTag
    from apps.notifications.models import Announcement, Notification
    from apps.projects.models import Project, ProjectMember, ProjectMembershipEvent, ProjectStageLog
    from apps.sensitive.models import SensitiveAccessRequest, SensitiveData
    from apps.tasks.models import Task
    from apps.users.models import User, UserLifecycleEvent, UserPreference

    stats = {'created': 0, 'updated': 0, 'deleted': 0}

    # 账号由完整种子建立并保留密码哈希；快照只覆盖非凭据资料。
    for row in snapshot.get('users', []):
        user = User.objects.filter(email=row['email']).first()
        if user is None:
            raise DemoBackupError(f'快照账号不存在：{row["email"]}')
        defaults = _row_defaults(User, row, exclude={'email'})
        User.objects.filter(pk=user.pk).update(**defaults)
        stats['updated'] += 1
    for row in snapshot.get('users', []):
        handover_email = row.get('handover_to__email')
        User.objects.filter(email=row['email']).update(
            handover_to_id=_optional_id(User, {'email': handover_email})
        )

    for row in snapshot.get('preferences', []):
        _upsert_snapshot_row(
            UserPreference,
            {'user_id': _required_id(User, {'email': row['user__email']}, row['user__email'])},
            row,
            exclude={'user'},
            stats=stats,
        )

    for row in snapshot.get('member_skills', []):
        skill, _ = SkillTag.objects.get_or_create(name=row['skill__name'])
        _upsert_snapshot_row(
            MemberSkill,
            {
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
                'skill_id': skill.pk,
            },
            row,
            stats=stats,
        )

    work_rows = snapshot.get('flexible_work_schedules', [])
    work_keys = {(row['user__email'], str(row['period_start'])) for row in work_rows}
    _delete_missing(
        FlexibleWorkSchedule.objects.filter(notes__startswith=DEMO_MARKER).select_related('user'),
        work_keys,
        lambda obj: (obj.user.email, obj.period_start.isoformat()),
        stats,
    )
    for row in work_rows:
        _upsert_snapshot_row(
            FlexibleWorkSchedule,
            {
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
                'period_start': row['period_start'],
            },
            row,
            exclude={'period_start'},
            stats=stats,
        )

    project_rows = snapshot.get('projects', [])
    project_codes = {row['code'] for row in project_rows}
    stale_projects = Project.all_objects.filter(code__startswith='TEAM-DEMO-').exclude(
        code__in=project_codes
    )
    stale_project_ids = list(stale_projects.values_list('id', flat=True))
    for asset in FileAsset.objects.filter(project__in=stale_projects).exclude(file=''):
        try:
            asset.file.delete(save=False)
        except (FileNotFoundError, OSError):
            pass
    if stale_project_ids:
        stale_ip = IntellectualPropertyApplication.objects.filter(
            related_project_id__in=stale_project_ids
        )
        for queryset in (
            PortalPublication.objects.filter(
                content_type=PortalPublication.ContentType.IP_APPLICATION,
                object_id__in=stale_ip.values_list('id', flat=True),
            ),
            IPObjection.objects.filter(application__in=stale_ip),
            IPMaterialVersion.objects.filter(application__in=stale_ip),
            IPReturnRecord.objects.filter(application__in=stale_ip),
            IPApplicationContributor.objects.filter(application__in=stale_ip),
            stale_ip,
            PortalPublication.objects.filter(
                content_type=PortalPublication.ContentType.PROJECT,
                object_id__in=stale_project_ids,
            ),
            RankingObjection.objects.filter(ranking__project_id__in=stale_project_ids),
            MemberRanking.objects.filter(project_id__in=stale_project_ids),
            Contribution.objects.filter(project_id__in=stale_project_ids),
            SensitiveAccessRequest.objects.filter(project_id__in=stale_project_ids),
            SensitiveData.objects.filter(project_id__in=stale_project_ids),
            FinanceReceipt.objects.filter(expense__project_id__in=stale_project_ids),
            FinanceExpense.all_objects.filter(project_id__in=stale_project_ids),
            FinanceIncome.objects.filter(project_id__in=stale_project_ids),
            FinanceBudget.objects.filter(project_id__in=stale_project_ids),
            Task.all_objects.filter(project_id__in=stale_project_ids),
            FileVersion.objects.filter(file_asset__project_id__in=stale_project_ids),
            FileAsset.objects.filter(project_id__in=stale_project_ids),
            Competition.objects.filter(project_id__in=stale_project_ids),
            ProjectMembershipEvent.objects.filter(
                membership__project_id__in=stale_project_ids
            ),
            ProjectStageLog.objects.filter(project_id__in=stale_project_ids),
            ProjectMember.objects.filter(project_id__in=stale_project_ids),
            Project.all_objects.filter(id__in=stale_project_ids),
        ):
            deleted, _ = queryset.delete()
            stats['deleted'] += deleted
    for row in project_rows:
        _upsert_snapshot_row(
            Project,
            {'code': row['code']},
            row,
            relations={
                'leader': _required_id(User, {'email': row['leader__email']}, row['leader__email'])
            },
            exclude={'code'},
            stats=stats,
        )

    team_rows = snapshot.get('teams', [])
    for row in team_rows:
        _upsert_snapshot_row(
            Team,
            {'code': row['code']},
            row,
            relations={
                'owner': _required_id(User, {'email': row['owner__email']}, row['owner__email'])
            },
            exclude={'code'},
            stats=stats,
        )

    project_member_rows = snapshot.get('project_members', [])
    project_member_keys = {
        (row['project__code'], row['user__email']) for row in project_member_rows
    }
    _delete_missing(
        ProjectMember.objects.filter(project__code__in=project_codes).select_related('project', 'user'),
        project_member_keys,
        lambda obj: (obj.project.code, obj.user.email),
        stats,
    )
    for row in project_member_rows:
        _upsert_snapshot_row(
            ProjectMember,
            {
                'project_id': _required_id(Project, {'code': row['project__code']}, row['project__code']),
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
            },
            row,
            exclude={'project', 'user'},
            stats=stats,
        )
    for row in project_member_rows:
        project_id = _required_id(Project, {'code': row['project__code']}, row['project__code'])
        member = ProjectMember.objects.get(
            project_id=project_id,
            user__email=row['user__email'],
        )
        handover_email = row.get('handover_to__user__email')
        handover_id = _optional_id(
            ProjectMember,
            {'project_id': project_id, 'user__email': handover_email},
        )
        ProjectMember.objects.filter(pk=member.pk).update(handover_to_id=handover_id)

    team_member_rows = snapshot.get('team_members', [])
    team_codes = {row['code'] for row in team_rows}
    team_member_keys = {(row['team__code'], row['user__email']) for row in team_member_rows}
    _delete_missing(
        TeamMember.objects.filter(team__code__in=team_codes).select_related('team', 'user'),
        team_member_keys,
        lambda obj: (obj.team.code, obj.user.email),
        stats,
    )
    for row in team_member_rows:
        _upsert_snapshot_row(
            TeamMember,
            {
                'team_id': _required_id(Team, {'code': row['team__code']}, row['team__code']),
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
            },
            row,
            exclude={'team', 'user'},
            stats=stats,
        )
    for row in team_member_rows:
        team_id = _required_id(Team, {'code': row['team__code']}, row['team__code'])
        member = TeamMember.objects.get(team_id=team_id, user__email=row['user__email'])
        TeamMember.objects.filter(pk=member.pk).update(
            handover_to_id=_optional_id(
                TeamMember,
                {'team_id': team_id, 'user__email': row.get('handover_to__user__email')},
            )
        )

    event_rows = snapshot.get('competition_events')
    if event_rows is not None:
        for row in event_rows:
            organization_id = _optional_id(
                Team,
                {'code': row.get('organization__code')},
            )
            _upsert_snapshot_row(
                CompetitionEvent,
                {
                    'organization_id': organization_id,
                    'name': row['name'],
                    'edition': str(row.get('edition') or ''),
                    'organizer': row.get('organizer') or '',
                },
                row,
                stats=stats,
            )

    competition_rows = snapshot.get('competitions', [])
    competition_keys = {
        _competition_snapshot_key(row)
        for row in competition_rows
    }
    current_competitions = list(
        Competition.objects.filter(
            project__code__in=project_codes,
        ).select_related(
            'project',
            'event',
            'event__organization',
        )
    )

    def current_competition_key(obj):
        event_key = _competition_object_key(obj, use_event_key=True)
        if event_key in competition_keys:
            return event_key
        return _competition_object_key(obj, use_event_key=False)

    stale_competition_ids = [
        obj.pk
        for obj in current_competitions
        if current_competition_key(obj) not in competition_keys
    ]
    if stale_competition_ids:
        FinanceExpense.all_objects.filter(
            competition_entry_id__in=stale_competition_ids,
        ).update(competition_entry_id=None)
        FinanceIncome.objects.filter(
            competition_entry_id__in=stale_competition_ids,
        ).update(competition_entry_id=None)
        # Competition-scoped files protect their entry. Remove only files
        # belonging to entries absent from the selected snapshot before
        # deleting those stale entries (notably when restoring a legacy v2
        # package over the richer current seed).
        stale_assets = FileAsset.all_objects.filter(
            competition_entry_id__in=stale_competition_ids,
        )
        for asset in stale_assets.exclude(file=''):
            try:
                asset.file.delete(save=False)
            except (FileNotFoundError, OSError):
                pass
        deleted, _ = FileVersion.objects.filter(
            file_asset__in=stale_assets,
        ).delete()
        stats['deleted'] += deleted
        deleted, _ = stale_assets.delete()
        stats['deleted'] += deleted

    _delete_missing(
        Competition.objects.filter(
            project__code__in=project_codes,
        ).select_related(
            'project',
            'event',
            'event__organization',
        ),
        competition_keys,
        current_competition_key,
        stats,
    )
    for row in competition_rows:
        natural_lookup = _competition_lookup_from_row(
            row,
            prefix='',
            project_model=Project,
            event_model=CompetitionEvent,
        )
        existing = Competition._base_manager.filter(
            **natural_lookup,
        ).order_by('pk').first()
        _upsert_snapshot_row(
            Competition,
            {'pk': existing.pk} if existing else natural_lookup,
            row,
            stats=stats,
        )

    if 'competition_participants' in snapshot:
        participant_rows = snapshot.get('competition_participants', [])
        participant_keys = {
            (
                _competition_snapshot_key(row, prefix='competition__'),
                row['user__email'],
            )
            for row in participant_rows
        }
        _delete_missing(
            CompetitionParticipant.objects.filter(
                competition__project__code__in=project_codes,
            ).select_related(
                'competition__project',
                'competition__event',
                'competition__event__organization',
                'user',
            ),
            participant_keys,
            lambda obj: (
                _competition_object_key(
                    obj.competition,
                    use_event_key=True,
                ),
                obj.user.email,
            ),
            stats,
        )
        for row in participant_rows:
            competition_id = _competition_id_from_row(
                row,
                prefix='competition__',
                competition_model=Competition,
                project_model=Project,
                event_model=CompetitionEvent,
            )
            _upsert_snapshot_row(
                CompetitionParticipant,
                {
                    'competition_id': competition_id,
                    'user_id': _required_id(
                        User,
                        {'email': row['user__email']},
                        row['user__email'],
                    ),
                },
                row,
                stats=stats,
            )

    if 'competition_awards' in snapshot:
        deleted, _ = CompetitionAward.objects.filter(
            competition__project__code__in=project_codes,
        ).delete()
        stats['deleted'] += deleted
        for row in snapshot.get('competition_awards', []):
            _upsert_snapshot_row(
                CompetitionAward,
                {
                    'competition_id': _competition_id_from_row(
                        row,
                        prefix='competition__',
                        competition_model=Competition,
                        project_model=Project,
                        event_model=CompetitionEvent,
                    ),
                    'award_name': row['award_name'],
                    'award_level': row.get('award_level') or '',
                    'award_date': row.get('award_date'),
                },
                row,
                stats=stats,
            )
        for row in snapshot.get('competition_award_recipients', []):
            award = CompetitionAward.objects.filter(
                competition_id=_competition_id_from_row(
                    row,
                    prefix='competition__',
                    competition_model=Competition,
                    project_model=Project,
                    event_model=CompetitionEvent,
                ),
                award_name=row['award_name'],
                award_level=row.get('award_level') or '',
                award_date=row.get('award_date'),
            ).order_by('pk').first()
            if award is None:
                raise DemoBackupError(
                    f'快照引用不存在：{row["award_name"]}'
                )
            award.recipients.add(
                _required_id(
                    User,
                    {'email': row['recipient__email']},
                    row['recipient__email'],
                )
            )
            stats['created'] += 1

    if event_rows is not None:
        event_keys = {
            (
                row.get('organization__code') or '',
                row['name'],
                str(row.get('edition') or ''),
                row.get('organizer') or '',
            )
            for row in event_rows
        }
        stale_event_ids = [
            event.pk
            for event in CompetitionEvent.objects.filter(
                organization__code__in=team_codes,
                entries__isnull=True,
            ).select_related('organization')
            if (
                event.organization.code if event.organization_id else '',
                event.name,
                str(event.edition),
                event.organizer or '',
            ) not in event_keys
        ]
        if stale_event_ids:
            deleted, _ = CompetitionEvent.objects.filter(
                pk__in=stale_event_ids,
            ).delete()
            stats['deleted'] += deleted

    task_rows = snapshot.get('tasks', [])
    task_keys = {(row['project__code'], row['title']) for row in task_rows}
    _delete_missing(
        Task.all_objects.filter(project__code__in=project_codes).select_related('project'),
        task_keys,
        lambda obj: (obj.project.code, obj.title),
        stats,
    )
    for row in task_rows:
        _upsert_snapshot_row(
            Task,
            {
                'project_id': _required_id(Project, {'code': row['project__code']}, row['project__code']),
                'title': row['title'],
            },
            row,
            relations={
                'assignee': _required_id(User, {'email': row['assignee__email']}, row['assignee__email']),
                'creator': _optional_id(User, {'email': row.get('creator__email')}),
                'reviewer': _optional_id(User, {'email': row.get('reviewer__email')}),
            },
            exclude={'title'},
            stats=stats,
        )

    for row in snapshot.get('finance_budgets', []):
        _upsert_snapshot_row(
            FinanceBudget,
            {'project_id': _required_id(Project, {'code': row['project__code']}, row['project__code'])},
            row,
            stats=stats,
        )

    expense_rows = snapshot.get('finance_expenses', [])
    expenses_include_competition_scope = any(
        'competition_entry__event__edition' in row
        for row in expense_rows
    )
    expense_keys = {
        (
            row['project__code'], row['title'],
            str(row['expense_date']), str(row['amount']),
        )
        for row in expense_rows
    }
    _delete_missing(
        FinanceExpense.all_objects.filter(project__code__in=project_codes).select_related('project'),
        expense_keys,
        lambda obj: (
            obj.project.code, obj.title,
            obj.expense_date.isoformat(), str(obj.amount),
        ),
        stats,
    )
    for row in expense_rows:
        expense_relations = {
            name: _optional_id(
                User,
                {'email': row.get(f'{name}__email')},
            )
            for name in ('spender', 'reviewer', 'applied_by', 'paid_by')
        }
        if expenses_include_competition_scope:
            expense_relations['competition_entry'] = (
                _competition_id_from_row(
                    row,
                    prefix='competition_entry__',
                    competition_model=Competition,
                    project_model=Project,
                    event_model=CompetitionEvent,
                )
                if row.get('competition_entry__project__code')
                else None
            )
        _upsert_snapshot_row(
            FinanceExpense,
            {
                'project_id': _required_id(Project, {'code': row['project__code']}, row['project__code']),
                'title': row['title'],
                'expense_date': row['expense_date'],
                'amount': row['amount'],
            },
            row,
            relations=expense_relations,
            exclude={'title', 'expense_date', 'amount'},
            stats=stats,
        )

    income_rows = snapshot.get('finance_incomes', [])
    incomes_include_competition_scope = any(
        'competition_entry__event__edition' in row
        for row in income_rows
    )
    income_keys = {
        (row['project__code'], row.get('reference_number') or row['title']) for row in income_rows
    }
    _delete_missing(
        FinanceIncome.objects.filter(project__code__in=project_codes).select_related('project'),
        income_keys,
        lambda obj: (obj.project.code, obj.reference_number or obj.title),
        stats,
    )
    for row in income_rows:
        project_id = _required_id(Project, {'code': row['project__code']}, row['project__code'])
        key_lookup = (
            {'project_id': project_id, 'reference_number': row['reference_number']}
            if row.get('reference_number')
            else {'project_id': project_id, 'title': row['title']}
        )
        income_relations = {
            'recorded_by': _optional_id(
                User,
                {'email': row.get('recorded_by__email')},
            ),
        }
        if incomes_include_competition_scope:
            income_relations['competition_entry'] = (
                _competition_id_from_row(
                    row,
                    prefix='competition_entry__',
                    competition_model=Competition,
                    project_model=Project,
                    event_model=CompetitionEvent,
                )
                if row.get('competition_entry__project__code')
                else None
            )
        _upsert_snapshot_row(
            FinanceIncome,
            key_lookup,
            row,
            relations=income_relations,
            stats=stats,
        )

    file_rows = snapshot.get('files', [])
    files_include_scope = any(
        'competition_entry__event__edition' in row
        for row in file_rows
    )

    def file_row_key(row):
        competition_key = None
        if (
            files_include_scope
            and row.get('competition_entry__project__code')
        ):
            competition_key = _competition_snapshot_key(
                row,
                prefix='competition_entry__',
            )
        return (row['project__code'], row['name'], competition_key)

    def file_object_key(obj):
        competition_key = None
        if files_include_scope and obj.competition_entry_id:
            competition_key = _competition_object_key(
                obj.competition_entry,
                use_event_key=True,
            )
        return (obj.project.code, obj.name, competition_key)

    file_keys = {file_row_key(row) for row in file_rows}
    _delete_missing(
        FileAsset.objects.filter(
            project__code__in=project_codes,
        ).select_related(
            'project',
            'competition_entry__project',
            'competition_entry__event',
            'competition_entry__event__organization',
        ),
        file_keys,
        file_object_key,
        stats,
        file_fields=('file',),
    )
    for row in file_rows:
        competition_id = None
        if (
            files_include_scope
            and row.get('competition_entry__project__code')
        ):
            competition_id = _competition_id_from_row(
                row,
                prefix='competition_entry__',
                competition_model=Competition,
                project_model=Project,
                event_model=CompetitionEvent,
            )
        asset_lookup = {
            'project_id': _required_id(
                Project,
                {'code': row['project__code']},
                row['project__code'],
            ),
            'name': row['name'],
        }
        relations = {
            'uploader': _optional_id(
                User,
                {'email': row.get('uploader__email')},
            ),
        }
        if files_include_scope:
            asset_lookup['competition_entry_id'] = competition_id
            relations['competition_entry'] = competition_id
            relations['team'] = _optional_id(
                Team,
                {'code': row.get('team__code')},
            )
        _upsert_snapshot_row(
            FileAsset,
            asset_lookup,
            row,
            relations=relations,
            exclude={'name'},
            stats=stats,
        )

    version_rows = snapshot.get('file_versions', [])
    versions_include_scope = any(
        'file_asset__competition_entry__event__edition' in row
        for row in version_rows
    )

    def version_row_asset_key(row):
        competition_key = None
        if (
            versions_include_scope
            and row.get(
                'file_asset__competition_entry__project__code'
            )
        ):
            competition_key = _competition_snapshot_key(
                row,
                prefix='file_asset__competition_entry__',
            )
        return (
            row['file_asset__project__code'],
            row['file_asset__name'],
            competition_key,
        )

    def version_object_asset_key(obj):
        competition_key = None
        if (
            versions_include_scope
            and obj.file_asset.competition_entry_id
        ):
            competition_key = _competition_object_key(
                obj.file_asset.competition_entry,
                use_event_key=True,
            )
        return (
            obj.file_asset.project.code,
            obj.file_asset.name,
            competition_key,
        )

    version_keys = {
        (*version_row_asset_key(row), row['version'])
        for row in version_rows
    }
    _delete_missing(
        FileVersion.objects.filter(file_asset__project__code__in=project_codes).select_related(
            'file_asset',
            'file_asset__project',
            'file_asset__competition_entry__project',
            'file_asset__competition_entry__event',
            'file_asset__competition_entry__event__organization',
        ),
        version_keys,
        lambda obj: (*version_object_asset_key(obj), obj.version),
        stats,
        file_fields=('file',),
    )
    for row in version_rows:
        asset_lookup = {
            'project__code': row['file_asset__project__code'],
            'name': row['file_asset__name'],
        }
        if versions_include_scope:
            competition_id = None
            if row.get(
                'file_asset__competition_entry__project__code'
            ):
                competition_id = _competition_id_from_row(
                    row,
                    prefix='file_asset__competition_entry__',
                    competition_model=Competition,
                    project_model=Project,
                    event_model=CompetitionEvent,
                )
            asset_lookup['competition_entry_id'] = competition_id
        asset_id = _required_id(
            FileAsset,
            asset_lookup,
            row['file_asset__name'],
        )
        _upsert_snapshot_row(
            FileVersion,
            {'file_asset_id': asset_id, 'version': row['version']},
            row,
            relations={'uploader': _optional_id(User, {'email': row.get('uploader__email')})},
            exclude={'version'},
            stats=stats,
        )

    receipt_rows = snapshot.get('finance_receipts', [])
    receipt_keys = {
        (
            row['expense__project__code'], row['expense__title'],
            str(row['expense__expense_date']), str(row['expense__amount']), row['file'],
        )
        for row in receipt_rows
    }
    _delete_missing(
        FinanceReceipt.objects.filter(expense__project__code__in=project_codes).select_related(
            'expense', 'expense__project'
        ),
        receipt_keys,
        lambda obj: (
            obj.expense.project.code, obj.expense.title,
            obj.expense.expense_date.isoformat(), str(obj.expense.amount), obj.file.name,
        ),
        stats,
        file_fields=('file',),
    )
    for row in receipt_rows:
        expense_id = _required_id(
            FinanceExpense,
            {
                'project__code': row['expense__project__code'],
                'title': row['expense__title'],
                'expense_date': row['expense__expense_date'],
                'amount': row['expense__amount'],
            },
            row['expense__title'],
        )
        _upsert_snapshot_row(
            FinanceReceipt,
            {'expense_id': expense_id, 'file': row['file']},
            row,
            relations={'uploaded_by': _optional_id(User, {'email': row.get('uploaded_by__email')})},
            exclude={'file'},
            stats=stats,
        )

    # 多对多关系按包内容全量替换。
    demo_tasks = Task.objects.filter(project__code__in=project_codes)
    task_attachment_through = Task.attachment_files.through
    task_collaborator_through = Task.collaborators.through
    deleted, _ = task_attachment_through.objects.filter(task__in=demo_tasks).delete()
    stats['deleted'] += deleted
    for row in snapshot.get('task_attachments', []):
        task_attachment_through.objects.create(
            task_id=_required_id(
                Task,
                {'project__code': row['task__project__code'], 'title': row['task__title']},
                row['task__title'],
            ),
            fileasset_id=_required_id(
                FileAsset,
                {'project__code': row['task__project__code'], 'name': row['fileasset__name']},
                row['fileasset__name'],
            ),
        )
        stats['created'] += 1
    deleted, _ = task_collaborator_through.objects.filter(task__in=demo_tasks).delete()
    stats['deleted'] += deleted
    for row in snapshot.get('task_collaborators', []):
        task_collaborator_through.objects.create(
            task_id=_required_id(
                Task,
                {'project__code': row['task__project__code'], 'title': row['task__title']},
                row['task__title'],
            ),
            user_id=_required_id(User, {'email': row['user__email']}, row['user__email']),
        )
        stats['created'] += 1

    sensitive_rows = snapshot.get('sensitive_data', [])
    for row in sensitive_rows:
        _upsert_snapshot_row(
            SensitiveData,
            {'title': row['title']},
            row,
            relations={
                'project': _optional_id(Project, {'code': row.get('project__code')}),
                'uploader': _optional_id(User, {'email': row.get('uploader__email')}),
                'file_attachment': _optional_id(
                    FileAsset,
                    {'project__code': row.get('project__code'), 'name': row.get('file_attachment__name')},
                ),
            },
            exclude={'title'},
            stats=stats,
        )

    request_rows = snapshot.get('sensitive_access_requests', [])
    request_keys = {
        (row['sensitive_data__title'], row['applicant__email'], row['is_download'])
        for row in request_rows
    }
    _delete_missing(
        SensitiveAccessRequest.objects.filter(sensitive_data__title__startswith=DEMO_MARKER).select_related(
            'sensitive_data', 'applicant'
        ),
        request_keys,
        lambda obj: (obj.sensitive_data.title, obj.applicant.email, obj.is_download),
        stats,
    )
    for row in request_rows:
        _upsert_snapshot_row(
            SensitiveAccessRequest,
            {
                'sensitive_data_id': _required_id(
                    SensitiveData, {'title': row['sensitive_data__title']}, row['sensitive_data__title']
                ),
                'applicant_id': _required_id(User, {'email': row['applicant__email']}, row['applicant__email']),
                'is_download': row['is_download'],
            },
            row,
            relations={
                'project': _optional_id(Project, {'code': row.get('project__code')}),
                'approver': _optional_id(User, {'email': row.get('approver__email')}),
            },
            exclude={'is_download'},
            stats=stats,
        )

    contribution_rows = snapshot.get('contributions', [])
    contribution_keys = {
        (row['project__code'], row['user__email'], row['period'], row['contribution_type'])
        for row in contribution_rows
    }
    _delete_missing(
        Contribution.objects.filter(project__code__in=project_codes).select_related('project', 'user'),
        contribution_keys,
        lambda obj: (obj.project.code, obj.user.email, obj.period, obj.contribution_type),
        stats,
    )
    for row in contribution_rows:
        _upsert_snapshot_row(
            Contribution,
            {
                'project_id': _required_id(Project, {'code': row['project__code']}, row['project__code']),
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
                'period': row['period'],
                'contribution_type': row['contribution_type'],
            },
            row,
            relations={
                'proof_file': _optional_id(
                    FileAsset,
                    {'project__code': row['project__code'], 'name': row.get('proof_file__name')},
                ),
                'filled_by': _optional_id(User, {'email': row.get('filled_by__email')}),
                'reviewer': _optional_id(User, {'email': row.get('reviewer__email')}),
            },
            exclude={'period', 'contribution_type'},
            stats=stats,
        )

    ranking_rows = snapshot.get('member_rankings', [])
    for row in ranking_rows:
        _upsert_snapshot_row(
            MemberRanking,
            {
                'project_id': _required_id(Project, {'code': row['project__code']}, row['project__code']),
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
                'period': row['period'],
            },
            row,
            relations={'confirmed_by': _optional_id(User, {'email': row.get('confirmed_by__email')})},
            exclude={'period'},
            stats=stats,
        )

    objection_rows = snapshot.get('ranking_objections', [])
    for row in objection_rows:
        ranking_id = _required_id(
            MemberRanking,
            {
                'project__code': row['ranking__project__code'],
                'user__email': row['ranking__user__email'],
                'period': row['ranking__period'],
            },
            row['ranking__user__email'],
        )
        _upsert_snapshot_row(
            RankingObjection,
            {
                'ranking_id': ranking_id,
                'objector_id': _required_id(User, {'email': row['objector__email']}, row['objector__email']),
            },
            row,
            relations={
                name: _optional_id(User, {'email': row.get(f'{name}__email')})
                for name in (
                    'leader_reviewer', 'teacher_confirmer',
                    'adjustment_applied_by', 'handler',
                )
            },
            stats=stats,
        )

    report_rows = snapshot.get('custom_reports', [])
    report_names = {row['name'] for row in report_rows}
    _delete_missing(
        CustomReport.objects.filter(name__startswith=DEMO_MARKER),
        report_names,
        lambda obj: obj.name,
        stats,
    )
    for row in report_rows:
        _upsert_snapshot_row(
            CustomReport,
            {'name': row['name']},
            row,
            relations={'created_by': _optional_id(User, {'email': row.get('created_by__email')})},
            exclude={'name'},
            stats=stats,
        )

    schedule_rows = snapshot.get('scheduled_reports', [])
    for row in schedule_rows:
        _upsert_snapshot_row(
            ScheduledReport,
            {'report_id': _required_id(CustomReport, {'name': row['report__name']}, row['report__name'])},
            row,
            relations={'created_by': _optional_id(User, {'email': row.get('created_by__email')})},
            stats=stats,
        )
    schedule_through = ScheduledReport.recipients.through
    demo_schedules = ScheduledReport.objects.filter(report__name__in=report_names)
    deleted, _ = schedule_through.objects.filter(scheduledreport__in=demo_schedules).delete()
    stats['deleted'] += deleted
    for row in snapshot.get('scheduled_report_recipients', []):
        schedule_through.objects.create(
            scheduledreport_id=_required_id(
                ScheduledReport, {'report__name': row['scheduledreport__report__name']}, row['scheduledreport__report__name']
            ),
            user_id=_required_id(User, {'email': row['user__email']}, row['user__email']),
        )
        stats['created'] += 1

    execution_rows = snapshot.get('scheduled_report_executions', [])
    execution_keys = {(row['schedule__report__name'], row['file_name']) for row in execution_rows}
    _delete_missing(
        ScheduledReportExecution.objects.filter(schedule__report__name__in=report_names).select_related(
            'schedule', 'schedule__report'
        ),
        execution_keys,
        lambda obj: (obj.schedule.report.name, obj.file_name),
        stats,
        file_fields=('file',),
    )
    for row in execution_rows:
        _upsert_snapshot_row(
            ScheduledReportExecution,
            {
                'schedule_id': _required_id(ScheduledReport, {'report__name': row['schedule__report__name']}, row['schedule__report__name']),
                'file_name': row['file_name'],
            },
            row,
            relations={'generated_by': _optional_id(User, {'email': row.get('generated_by__email')})},
            exclude={'file_name'},
            stats=stats,
        )

    ip_rows = snapshot.get('ip_applications', [])
    for row in ip_rows:
        _upsert_snapshot_row(
            IntellectualPropertyApplication,
            {'application_code': row['application_code']},
            row,
            relations={
                'related_project': _optional_id(Project, {'code': row.get('related_project__code')}),
                'main_writer': _optional_id(User, {'email': row.get('main_writer__email')}),
                'applicant_executor': _optional_id(User, {'email': row.get('applicant_executor__email')}),
                'material_manager': _optional_id(User, {'email': row.get('material_manager__email')}),
                'project_reviewer': _optional_id(User, {'email': row.get('project_reviewer__email')}),
                'teacher_confirmer': _optional_id(User, {'email': row.get('teacher_confirmer__email')}),
                'final_certificate_file': _optional_id(
                    FileAsset,
                    {'project__code': row.get('related_project__code'), 'name': row.get('final_certificate_file__name')},
                ),
                'created_by': _optional_id(User, {'email': row.get('created_by__email')}),
            },
            exclude={'application_code'},
            stats=stats,
        )

    contributor_rows = snapshot.get('ip_contributors', [])
    for row in contributor_rows:
        _upsert_snapshot_row(
            IPApplicationContributor,
            {
                'application_id': _required_id(IntellectualPropertyApplication, {'application_code': row['application__application_code']}, row['application__application_code']),
                'user_id': _required_id(User, {'email': row['user__email']}, row['user__email']),
                'role': row['role'],
            },
            row,
            relations={'confirmed_by': _optional_id(User, {'email': row.get('confirmed_by__email')})},
            exclude={'role'},
            stats=stats,
        )

    for row in snapshot.get('ip_material_versions', []):
        application_id = _required_id(
            IntellectualPropertyApplication,
            {'application_code': row['application__application_code']},
            row['application__application_code'],
        )
        _upsert_snapshot_row(
            IPMaterialVersion,
            {
                'application_id': application_id,
                'material_type': row['material_type'],
                'version': row['version'],
            },
            row,
            relations={
                'file_asset': _required_id(
                    FileAsset,
                    {'project__code': row['application__application_code'].replace('IP-', '', 1), 'name': row['file_asset__name']},
                    row['file_asset__name'],
                ) if not FileAsset.objects.filter(name=row['file_asset__name']).count() == 1 else FileAsset.objects.get(name=row['file_asset__name']).pk,
                'uploaded_by': _optional_id(User, {'email': row.get('uploaded_by__email')}),
            },
            exclude={'material_type', 'version'},
            stats=stats,
        )

    for row in snapshot.get('ip_return_records', []):
        application_id = _required_id(
            IntellectualPropertyApplication,
            {'application_code': row['application__application_code']},
            row['application__application_code'],
        )
        existing = IPReturnRecord.objects.filter(application_id=application_id).order_by('pk').first()
        lookup = {'pk': existing.pk} if existing else {'application_id': application_id, 'return_time': row['return_time']}
        _upsert_snapshot_row(
            IPReturnRecord,
            lookup,
            row,
            relations={
                'application': application_id,
                'responsible_user': _optional_id(User, {'email': row.get('responsible_user__email')}),
                'assigned_by': _optional_id(User, {'email': row.get('assigned_by__email')}),
                'actual_modifier': _optional_id(User, {'email': row.get('actual_modifier__email')}),
                'proof_file': _optional_id(FileAsset, {'name': row.get('proof_file__name')}),
            },
            stats=stats,
        )

    for row in snapshot.get('ip_objections', []):
        _upsert_snapshot_row(
            IPObjection,
            {
                'application_id': _required_id(IntellectualPropertyApplication, {'application_code': row['application__application_code']}, row['application__application_code']),
                'objector_id': _required_id(User, {'email': row['objector__email']}, row['objector__email']),
                'objection_type': row['objection_type'],
            },
            row,
            relations={
                'leader_reviewer': _optional_id(User, {'email': row.get('leader_reviewer__email')}),
                'teacher_confirmer': _optional_id(User, {'email': row.get('teacher_confirmer__email')}),
            },
            exclude={'objection_type'},
            stats=stats,
        )

    for row in snapshot.get('portal_settings', []):
        _upsert_snapshot_row(
            PortalSettings,
            {'singleton_key': row['singleton_key']},
            row,
            relations={'updated_by': _optional_id(User, {'email': row.get('updated_by__email')})},
            exclude={'singleton_key'},
            stats=stats,
        )

    publication_rows = snapshot.get('portal_publications', [])
    current_publication_ids = list(
        PortalPublication.objects.filter(
            Q(content_type=PortalPublication.ContentType.PROJECT, object_id__in=Project.objects.filter(code__in=project_codes).values('id'))
            | Q(content_type=PortalPublication.ContentType.IP_APPLICATION, object_id__in=IntellectualPropertyApplication.objects.filter(application_code__in=[row['application_code'] for row in ip_rows]).values('id'))
            | Q(content_type=PortalPublication.ContentType.MEMBER, object_id__in=User.objects.filter(email__in=DEMO_ACCOUNT_EMAILS).values('id'))
        ).values_list('id', flat=True)
    )
    if current_publication_ids:
        deleted, _ = PortalPublication.objects.filter(pk__in=current_publication_ids).delete()
        stats['deleted'] += deleted
    for row in publication_rows:
        content_type = row['content_type']
        object_key = row.get('object_key')
        if not object_key:
            if content_type == PortalPublication.ContentType.PROJECT:
                object_key = next((item['code'] for item in project_rows if item['name'] == row.get('custom_title')), '')
            elif content_type == PortalPublication.ContentType.IP_APPLICATION:
                object_key = next((item['application_code'] for item in ip_rows if item['title'] == row.get('custom_title')), '')
            elif content_type == PortalPublication.ContentType.MEMBER:
                object_key = next((item['email'] for item in snapshot.get('users', []) if item['name'] == row.get('custom_title')), '')
        model_lookup = {
            PortalPublication.ContentType.PROJECT: (Project, {'code': object_key}),
            PortalPublication.ContentType.IP_APPLICATION: (IntellectualPropertyApplication, {'application_code': object_key}),
            PortalPublication.ContentType.MEMBER: (User, {'email': object_key}),
        }.get(content_type)
        if not model_lookup:
            continue
        target_model, lookup = model_lookup
        object_id = _required_id(target_model, lookup, str(object_key))
        _upsert_snapshot_row(
            PortalPublication,
            {'content_type': content_type, 'object_id': object_id},
            row,
            relations={'updated_by': _optional_id(User, {'email': row.get('updated_by__email')})},
            exclude={'content_type', 'object_id'},
            stats=stats,
        )

    # 历史表没有业务唯一键，按包内容删除后重建。
    demo_project_members = ProjectMember.objects.filter(project__code__in=project_codes)
    _replace_history_rows(
        ProjectMembershipEvent,
        ProjectMembershipEvent.objects.filter(membership__in=demo_project_members),
        snapshot.get('project_membership_events', []),
        lambda row: {
            'membership': _required_id(ProjectMember, {'project__code': row['membership__project__code'], 'user__email': row['membership__user__email']}, row['membership__user__email']),
            'handover_to': _optional_id(ProjectMember, {'project__code': row['membership__project__code'], 'user__email': row.get('handover_to__user__email')}),
            'operator': _optional_id(User, {'email': row.get('operator__email')}),
        },
        stats,
    )
    _replace_history_rows(
        ProjectStageLog,
        ProjectStageLog.objects.filter(project__code__in=project_codes),
        snapshot.get('project_stage_logs', []),
        lambda row: {
            'project': _required_id(Project, {'code': row['project__code']}, row['project__code']),
            'operator': _optional_id(User, {'email': row.get('operator__email')}),
        },
        stats,
    )
    _replace_history_rows(
        UserLifecycleEvent,
        UserLifecycleEvent.objects.filter(user__email__in=DEMO_ACCOUNT_EMAILS),
        snapshot.get('user_lifecycle_events', []),
        lambda row: {
            'user': _required_id(User, {'email': row['user__email']}, row['user__email']),
            'handover_to': _optional_id(User, {'email': row.get('handover_to__email')}),
            'operator': _optional_id(User, {'email': row.get('operator__email')}),
        },
        stats,
    )
    demo_team_members = TeamMember.objects.filter(team__code__in=team_codes)
    _replace_history_rows(
        TeamMembershipEvent,
        TeamMembershipEvent.objects.filter(membership__in=demo_team_members),
        snapshot.get('team_membership_events', []),
        lambda row: {
            'membership': _required_id(TeamMember, {'team__code': row['membership__team__code'], 'user__email': row['membership__user__email']}, row['membership__user__email']),
            'handover_to': _optional_id(TeamMember, {'team__code': row['membership__team__code'], 'user__email': row.get('handover_to__user__email')}),
            'operator': _optional_id(User, {'email': row.get('operator__email')}),
        },
        stats,
    )

    # 标题在演示种子中唯一；先保留种子生成的关联对象 ID，再覆盖包内状态。
    notification_rows = snapshot.get('notifications', [])
    notification_keys = {(row.get('recipient__email'), row['title']) for row in notification_rows}
    _delete_missing(
        Notification.objects.filter(title__startswith=DEMO_MARKER).select_related('recipient'),
        notification_keys,
        lambda obj: (obj.recipient.email if obj.recipient_id else None, obj.title),
        stats,
    )
    for row in notification_rows:
        recipient_id = _optional_id(User, {'email': row.get('recipient__email')})
        existing = Notification.objects.filter(recipient_id=recipient_id, title=row['title']).first()
        related_id = _resolve_related_object_id(row)
        relations = {
            'recipient': recipient_id,
            'sender': _optional_id(User, {'email': row.get('sender__email')}),
        }
        lookup = {'pk': existing.pk} if existing else {'recipient_id': recipient_id, 'title': row['title']}
        imported_row = dict(row)
        if related_id is not None:
            imported_row['related_object_id'] = related_id
        elif existing:
            imported_row.pop('related_object_id', None)
        else:
            imported_row['related_object_id'] = None
        _upsert_snapshot_row(Notification, lookup, imported_row, relations=relations, stats=stats)

    announcement_rows = snapshot.get('announcements', [])
    announcement_titles = {row['title'] for row in announcement_rows}
    _delete_missing(
        Announcement.objects.filter(title__startswith=DEMO_MARKER),
        announcement_titles,
        lambda obj: obj.title,
        stats,
    )
    for row in announcement_rows:
        _upsert_snapshot_row(
            Announcement,
            {'title': row['title']},
            row,
            relations={'author': _optional_id(User, {'email': row.get('author__email')})},
            exclude={'title'},
            stats=stats,
        )

    import_rows = snapshot.get('imports', [])
    for row in import_rows:
        _upsert_snapshot_row(
            ImportTask,
            {'module': row['module'], 'created_by_id': _optional_id(User, {'email': row.get('created_by__email')})},
            row,
            stats=stats,
        )

    log_rows = snapshot.get('operation_logs', [])
    deleted, _ = OperationLog.objects.filter(description__startswith=DEMO_MARKER).delete()
    stats['deleted'] += deleted
    for row in log_rows:
        _upsert_snapshot_row(
            OperationLog,
            {
                'description': row['description'],
                'request_path': row['request_path'],
                'operator_id': _optional_id(User, {'email': row.get('operator__email')}),
            },
            row,
            stats=stats,
        )

    return stats


def _resolve_related_object_id(row: dict):
    key = row.get('related_object_key')
    if not isinstance(key, dict):
        return None
    related_type = row.get('related_object_type')
    if related_type == 'project':
        from apps.projects.models import Project
        return _optional_id(Project, {'code': key.get('code')})
    if related_type == 'task':
        from apps.tasks.models import Task
        return _optional_id(Task, {'project__code': key.get('project'), 'title': key.get('title')})
    if related_type == 'competition':
        from apps.competitions.models import Competition

        lookup = {
            'project__code': key.get('project'),
            'name': key.get('name'),
        }
        if key.get('event_name') and key.get('event_edition'):
            lookup = {
                'project__code': key.get('project'),
                'event__name': key.get('event_name'),
                'event__edition': str(key.get('event_edition')),
                'event__organizer': key.get('event_organizer') or '',
                'entry_name': key.get('entry_name') or '',
            }
            if key.get('event_organization'):
                lookup['event__organization__code'] = key[
                    'event_organization'
                ]
            else:
                lookup['event__organization__isnull'] = True
        elif key.get('register_date'):
            lookup['register_date'] = key['register_date']
        return _optional_id(Competition, lookup)
    if related_type == 'finance_expense':
        from apps.finance.models import FinanceExpense
        return _optional_id(FinanceExpense, {
            'project__code': key.get('project'),
            'title': key.get('title'),
            'expense_date': key.get('expense_date'),
            'amount': key.get('amount'),
        })
    if related_type == 'contribution':
        from apps.contributions.models import Contribution
        return _optional_id(Contribution, {
            'project__code': key.get('project'), 'user__email': key.get('user'),
            'period': key.get('period'), 'contribution_type': key.get('type'),
        })
    if related_type == 'ip_application':
        from apps.intellectual_property.models import IntellectualPropertyApplication
        return _optional_id(IntellectualPropertyApplication, {'application_code': key.get('application_code')})
    if related_type == 'sensitive_request':
        from apps.sensitive.models import SensitiveAccessRequest
        return _optional_id(SensitiveAccessRequest, {
            'sensitive_data__title': key.get('title'),
            'applicant__email': key.get('applicant'),
            'is_download': key.get('is_download'),
        })
    if related_type == 'ranking_objection':
        from apps.contributions.models import RankingObjection
        return _optional_id(RankingObjection, {
            'ranking__project__code': key.get('project'),
            'ranking__user__email': key.get('user'),
            'ranking__period': key.get('period'),
            'objector__email': key.get('objector'),
        })
    if related_type == 'work_schedule':
        from apps.members.models import FlexibleWorkSchedule
        return _optional_id(FlexibleWorkSchedule, {
            'user__email': key.get('user'), 'period_start': key.get('period_start'),
        })
    return None


def _legacy_storage_names(snapshot: dict) -> dict:
    names = {}
    section_map = {
        'assets': ('files', 'file'),
        'versions': ('file_versions', 'file'),
        'receipts': ('finance_receipts', 'file'),
        'scheduled_reports': ('scheduled_report_executions', 'file'),
        'avatars': ('users', 'avatar'),
        'team_logos': ('teams', 'logo'),
    }
    for kind, (section, field_name) in section_map.items():
        for row in snapshot.get(section, []):
            storage_name = row.get(field_name)
            if storage_name:
                names.setdefault((kind, Path(storage_name).name), []).append(storage_name)
    return names


def _restore_media_files(path: Path, manifest: dict, snapshot: dict) -> int:
    media_root = Path(settings.MEDIA_ROOT).resolve()
    media_root.mkdir(parents=True, exist_ok=True)
    legacy_names = _legacy_storage_names(snapshot)
    restored = 0
    with zipfile.ZipFile(path, 'r') as archive:
        for entry in manifest.get('entries', []):
            archive_path = entry.get('path', '')
            if not archive_path.startswith('media/'):
                continue
            storage_name = entry.get('storage_name') or ''
            if not storage_name:
                parts = archive_path.split('/', 2)
                if len(parts) != 3:
                    continue
                archived_name = Path(parts[2]).name.partition('_')[2]
                candidates = legacy_names.get((parts[1], archived_name), [])
                storage_name = candidates.pop(0) if candidates else ''
            if not storage_name:
                continue
            relative = Path(str(storage_name).replace('\\', '/'))
            if relative.is_absolute() or '..' in relative.parts:
                raise DemoBackupError(f'备份附件路径无效：{storage_name}')
            target = (media_root / relative).resolve()
            if not target.is_relative_to(media_root):
                raise DemoBackupError(f'备份附件路径越界：{storage_name}')
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(archive_path)
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=target.parent,
                    suffix='.restore.tmp',
                    delete=False,
                ) as temp:
                    temp.write(content)
                    temp_path = Path(temp.name)
                os.replace(temp_path, target)
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
            restored += 1
    return restored


def _restore_verified_package(path: Path, manifest: dict) -> dict:
    snapshot = _read_snapshot(path)
    with transaction.atomic():
        call_command('seed_demo_data', clean=True, force=True, verbosity=0)
        stats = _restore_snapshot_overlay(snapshot)
        media_count = _restore_media_files(path, manifest, snapshot)
    return {'records': stats, 'media_files': media_count}


def restore_demo_backup(backup_id: str, *, requested_by=None) -> dict:
    """恢复所选包的业务快照与附件；失败时自动恢复操作前状态。"""
    manifest = verify_demo_backup(backup_id)
    rollback = create_demo_backup(created_by=requested_by, reason=f'before-restore:{backup_id}')
    path = _safe_backup_path(backup_id)
    try:
        restored = _restore_verified_package(path, manifest)
    except Exception as restore_exc:
        rollback_id = rollback['backup_id']
        try:
            rollback_manifest = verify_demo_backup(rollback_id)
            _restore_verified_package(_safe_backup_path(rollback_id), rollback_manifest)
        except Exception as rollback_exc:
            raise DemoBackupError(
                f'恢复失败且自动回滚失败：{restore_exc}；回滚错误：{rollback_exc}'
            ) from restore_exc
        raise DemoBackupError(f'恢复失败，已自动回滚：{restore_exc}') from restore_exc
    return {
        'backup_id': backup_id,
        'status': 'restored',
        'restored_at': timezone.now().isoformat(),
        'strategy': manifest['restore_strategy'],
        'restored_records': restored['records'],
        'restored_media_files': restored['media_files'],
        'rollback_backup_id': rollback['backup_id'],
        'requires_relogin': True,
    }


def get_backup_file(backup_id: str) -> Path:
    path = _safe_backup_path(backup_id)
    if not path.exists():
        raise DemoBackupError('备份包不存在')
    return path
