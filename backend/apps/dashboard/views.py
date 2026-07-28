"""
驾驶舱看板视图
返回项目总览、经费总表、任务状态、人员状态、风险提醒、公告区等聚合数据
"""
import os
import subprocess
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.schema import success_response_schema
from common.permissions import IsInternalTeamMember, IsTeacherOrAdmin
from common.project_access import (
    active_user_root_team_ids,
    scope_project_queryset,
)
from apps.common.team_models import Team, TeamMember
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget, FinanceExpense
from apps.competitions.models import Competition
from apps.users.models import User
from apps.notifications.models import Announcement
from apps.notifications.announcement_access import scope_announcements_for_user


class DashboardNamedCountSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()


class DashboardProjectOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    paused = serializers.IntegerField()
    closed = serializers.IntegerField()
    awarded = serializers.IntegerField()
    stage_distribution = serializers.DictField(
        child=DashboardNamedCountSerializer(),
    )


class DashboardProjectFinanceSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    bonus_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    other_income = serializers.DecimalField(max_digits=14, decimal_places=2)
    planned_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_basis = serializers.DecimalField(max_digits=14, decimal_places=2)
    used_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    committed_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    remaining_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    available_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    status = serializers.CharField()
    status_display = serializers.CharField()


class DashboardFinanceOverviewSerializer(serializers.Serializer):
    total_bonus = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_other_income = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_used = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_pending = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_planned = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_committed = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_available = serializers.DecimalField(max_digits=14, decimal_places=2)
    project_finance = DashboardProjectFinanceSerializer(many=True)


class DashboardTaskOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    overdue = serializers.IntegerField()
    upcoming_deadline = serializers.IntegerField()
    status_distribution = serializers.DictField(
        child=DashboardNamedCountSerializer(),
    )


class DashboardTopMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    project_count = serializers.IntegerField()


class DashboardMemberOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    teacher = serializers.IntegerField()
    member = serializers.IntegerField()
    admin = serializers.IntegerField()
    student = serializers.IntegerField()
    top_members = DashboardTopMemberSerializer(many=True)


class DashboardRiskSerializer(serializers.Serializer):
    type = serializers.CharField()
    message = serializers.CharField()
    project_id = serializers.IntegerField(required=False)
    project_name = serializers.CharField(required=False)
    last_update = serializers.CharField(required=False)
    task_id = serializers.IntegerField(required=False)
    task_title = serializers.CharField(required=False)
    deadline = serializers.CharField(required=False, allow_null=True)
    competition_id = serializers.IntegerField(required=False)
    competition_name = serializers.CharField(required=False)
    defense_date = serializers.CharField(required=False, allow_null=True)


class DashboardRiskOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    items = DashboardRiskSerializer(many=True)


class DashboardAnnouncementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    content = serializers.CharField()
    category = serializers.CharField()
    category_display = serializers.CharField()
    is_pinned = serializers.BooleanField()
    is_public = serializers.BooleanField()
    author_name = serializers.CharField(allow_blank=True)
    published_at = serializers.CharField(allow_null=True)


class DashboardAnnouncementOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    items = DashboardAnnouncementSerializer(many=True)


class DashboardDataSerializer(serializers.Serializer):
    project_overview = DashboardProjectOverviewSerializer()
    finance_overview = DashboardFinanceOverviewSerializer()
    task_overview = DashboardTaskOverviewSerializer()
    member_overview = DashboardMemberOverviewSerializer()
    risk_alerts = DashboardRiskOverviewSerializer()
    announcements = DashboardAnnouncementOverviewSerializer()
    generated_at = serializers.CharField()


class DashboardView(APIView):
    """
    驾驶舱看板
    GET /api/v1/dashboard/
    返回聚合数据：项目总览、经费总表、任务状态、人员状态、风险提醒、公告区
    """
    permission_classes = [IsInternalTeamMember]

    @extend_schema(
        responses={
            200: success_response_schema(
                'DashboardResponse', DashboardDataSerializer(),
            ),
        },
    )
    def get(self, request):
        """获取驾驶舱聚合数据"""
        now = timezone.now()
        # 真实团队规则：项目超过 11 天未更新视为陈旧
        stale_threshold = now - timedelta(days=11)
        # 30天前
        month_ago = now - timedelta(days=30)
        project_id = request.query_params.get('project_id')
        try:
            project_id = int(project_id) if project_id else None
        except (TypeError, ValueError):
            return error_response(message='project_id must be an integer', code=1001)

        # ============ 1. 项目总览 ============
        project_queryset = scope_project_queryset(
            Project.objects.all(),
            request.user,
            project_lookup='',
        )
        task_queryset = scope_project_queryset(
            Task.objects.all(),
            request.user,
            project_lookup='project',
        )
        budget_queryset = scope_project_queryset(
            FinanceBudget.objects.all(),
            request.user,
            project_lookup='project',
        )
        if project_id:
            if not project_queryset.filter(pk=project_id).exists():
                return error_response(
                    message='项目不存在或无权查看',
                    code=1004,
                    http_status=404,
                )
            project_queryset = project_queryset.filter(pk=project_id)
            task_queryset = task_queryset.filter(project_id=project_id)
            budget_queryset = budget_queryset.filter(project_id=project_id)
        total_projects = project_queryset.count()
        active_projects = project_queryset.filter(status=Project.Status.ACTIVE).count()
        paused_projects = project_queryset.filter(status=Project.Status.PAUSED).count()
        closed_projects = project_queryset.filter(status=Project.Status.CLOSED).count()
        awarded_projects = project_queryset.filter(
            current_stage=Project.Stage.AWARDED
        ).count()

        # 各阶段项目分布
        stage_distribution = {}
        for stage_code, stage_name in Project.Stage.choices:
            stage_distribution[stage_code] = {
                'name': stage_name,
                'count': project_queryset.filter(current_stage=stage_code).count(),
            }

        project_overview = {
            'total': total_projects,
            'active': active_projects,
            'paused': paused_projects,
            'closed': closed_projects,
            'awarded': awarded_projects,
            'stage_distribution': stage_distribution,
        }

        # ============ 2. 经费总表（所有项目汇总）============
        budgets = budget_queryset
        total_bonus = budgets.aggregate(total=Sum('bonus_amount'))['total'] or 0
        total_other_income = budgets.aggregate(total=Sum('other_income'))['total'] or 0
        total_used = budgets.aggregate(total=Sum('used_amount'))['total'] or 0
        total_pending = budgets.aggregate(total=Sum('pending_reimbursement'))['total'] or 0
        total_income = total_bonus + total_other_income
        total_remaining = total_income - total_used
        total_planned = sum((budget.budget_basis for budget in budgets), 0)
        total_committed = sum((budget.committed_amount for budget in budgets), 0)
        total_available = sum((budget.available_amount for budget in budgets), 0)

        # 各项目经费明细
        project_finance = []
        for budget in budgets.select_related('project'):
            project_finance.append({
                'project_id': budget.project_id,
                'project_name': budget.project.name,
                'bonus_amount': str(budget.bonus_amount),
                'other_income': str(budget.other_income),
                'planned_amount': str(budget.planned_amount),
                'budget_basis': str(budget.budget_basis),
                'used_amount': str(budget.used_amount),
                'committed_amount': str(budget.committed_amount),
                'remaining_amount': str(budget.remaining_amount),
                'available_amount': str(budget.available_amount),
                'status': budget.status,
                'status_display': budget.get_status_display(),
            })

        finance_overview = {
            'total_bonus': str(total_bonus),
            'total_other_income': str(total_other_income),
            'total_income': str(total_income),
            'total_used': str(total_used),
            'total_pending': str(total_pending),
            'total_remaining': str(total_remaining),
            'total_planned': str(total_planned),
            'total_committed': str(total_committed),
            'total_available': str(total_available),
            'project_finance': project_finance,
        }

        # ============ 3. 任务状态（当前任务统计）============
        task_stats = {}
        for status_code, status_name in Task.Status.choices:
            task_stats[status_code] = {
                'name': status_name,
                'count': task_queryset.filter(status=status_code).count(),
            }

        total_tasks = task_queryset.count()
        overdue_tasks = task_queryset.filter(status=Task.Status.OVERDUE).count()
        # 即将到期任务（3天内）
        soon_deadline = now + timedelta(days=3)
        upcoming_deadline_tasks = task_queryset.filter(
            deadline__lte=soon_deadline,
            deadline__gte=now,
            status__in=[Task.Status.TODO, Task.Status.DOING, Task.Status.PENDING_REVIEW],
        ).count()

        task_overview = {
            'total': total_tasks,
            'overdue': overdue_tasks,
            'upcoming_deadline': upcoming_deadline_tasks,
            'status_distribution': task_stats,
        }

        # ============ 4. 人员状态 ============
        member_queryset = User.objects.filter(is_active=True)
        if request.user.global_role not in ('teacher', 'sys_admin'):
            root_ids = active_user_root_team_ids(request.user)
            if root_ids:
                member_queryset = member_queryset.filter(
                    Q(
                        teammember__team_id__in=root_ids,
                        teammember__status__in=[
                            TeamMember.Status.ACTIVE,
                            TeamMember.Status.ON_LEAVE,
                        ],
                    )
                    | Q(
                        teammember__team__parent_id__in=root_ids,
                        teammember__status__in=[
                            TeamMember.Status.ACTIVE,
                            TeamMember.Status.ON_LEAVE,
                        ],
                    )
                    | Q(owned_teams__id__in=root_ids)
                    | Q(owned_teams__parent_id__in=root_ids)
                ).distinct()
            elif Team.objects.filter(parent__isnull=True, is_active=True).exists():
                member_queryset = member_queryset.none()

        total_members = member_queryset.count()
        teacher_count = member_queryset.filter(
            is_active=True, global_role=User.GlobalRole.TEACHER
        ).count()
        member_count = member_queryset.filter(
            is_active=True, global_role=User.GlobalRole.MEMBER
        ).count()
        admin_count = member_queryset.filter(
            is_active=True, global_role=User.GlobalRole.SYS_ADMIN
        ).count()
        student_count = member_queryset.filter(is_active=True, is_student=True).count()

        # 各成员参与项目数
        member_project_counts = []
        visible_project_ids = project_queryset.values_list('id', flat=True)
        for user in member_queryset.annotate(
            project_count=Count(
                'project_memberships',
                filter=Q(
                    project_memberships__project_id__in=visible_project_ids,
                    project_memberships__status=ProjectMember.Status.ACTIVE,
                ),
                distinct=True,
            )
        ).order_by('-project_count')[:10]:
            member_project_counts.append({
                'user_id': user.id,
                'name': user.name,
                'project_count': user.project_count,
            })

        member_overview = {
            'total': total_members,
            'teacher': teacher_count,
            'member': member_count,
            'admin': admin_count,
            'student': student_count,
            'top_members': member_project_counts,
        }

        # ============ 5. 风险提醒 ============
        risks = []

        # 未更新项目（超过 11 天未打卡）
        stale_projects = project_queryset.filter(
            status=Project.Status.ACTIVE,
        ).filter(
            Q(last_leader_update__lte=stale_threshold)
            | Q(last_leader_update__isnull=True, created_at__lte=stale_threshold)
        )
        for project in stale_projects:
            update_baseline = project.last_leader_update or project.created_at
            risks.append({
                'type': 'stale_project',
                'message': f'项目"{project.name}"已超过11天未更新',
                'project_id': project.id,
                'project_name': project.name,
                'last_update': update_baseline.strftime('%Y-%m-%d %H:%M'),
            })

        # 延期任务
        overdue_task_list = task_queryset.filter(status=Task.Status.OVERDUE)[:20]
        for task in overdue_task_list:
            risks.append({
                'type': 'overdue_task',
                'message': f'任务"{task.title}"已逾期',
                'task_id': task.id,
                'task_title': task.title,
                'deadline': task.deadline.strftime('%Y-%m-%d %H:%M') if task.deadline else None,
            })

        # 临近比赛
        upcoming_competitions = scope_project_queryset(
            Competition.objects.filter(
            status__in=[Competition.Status.PREPARING, Competition.Status.ONGOING],
            defense_date__gte=now.date(),
            defense_date__lte=(now + timedelta(days=30)).date(),
            ),
            request.user,
            project_lookup='project',
        )
        if project_id:
            upcoming_competitions = upcoming_competitions.filter(project_id=project_id)
        upcoming_competitions = upcoming_competitions.order_by('defense_date')[:10]
        for comp in upcoming_competitions:
            risks.append({
                'type': 'upcoming_competition',
                'message': f'比赛"{comp.name}"临近答辩日期',
                'competition_id': comp.id,
                'competition_name': comp.name,
                'defense_date': comp.defense_date.strftime('%Y-%m-%d') if comp.defense_date else None,
            })

        risk_alerts = {
            'total': len(risks),
            'items': risks,
        }

        # ============ 6. 公告区 ============
        # 已发布公告，按置顶优先、发布时间倒序取最新 5 条
        visible_announcements = scope_announcements_for_user(
            Announcement.objects.select_related(
                'author',
                'organization',
            ).prefetch_related('target_teams', 'target_projects'),
            request.user,
        )
        latest_announcements = visible_announcements.order_by(
            '-is_pinned',
            '-published_at',
            '-created_at',
        )[:5]
        announcement_items = []
        for ann in latest_announcements:
            announcement_items.append({
                'id': ann.id,
                'title': ann.title,
                'content': ann.content,
                'category': ann.category,
                'category_display': ann.get_category_display(),
                'is_pinned': ann.is_pinned,
                'is_public': ann.is_public,
                'author_name': ann.author.name if ann.author else '',
                'published_at': ann.published_at.strftime('%Y-%m-%d %H:%M') if ann.published_at else None,
            })

        announcements = {
            'total': visible_announcements.count(),
            'items': announcement_items,
        }

        # ============ 汇总返回 ============
        data = {
            'project_overview': project_overview,
            'finance_overview': finance_overview,
            'task_overview': task_overview,
            'member_overview': member_overview,
            'risk_alerts': risk_alerts,
            'announcements': announcements,
            'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        }

        return success_response(data, message='success')


class SystemInfoView(APIView):
    """
    系统信息接口（P19）
    GET /api/v1/dashboard/system-info/
    返回: 版本号、Git 分支、Django 版本、已安装应用数量
    权限：老师或管理员
    """

    permission_classes = [IsTeacherOrAdmin]

    @staticmethod
    def _read_version():
        """读取 VERSION 文件中的版本号"""
        version_file = settings.BASE_DIR / 'VERSION'
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('VERSION='):
                        return line.split('=', 1)[1].strip()
            # 兜底：取第一个非注释非空行
            with open(version_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        return line
        except OSError:
            return 'unknown'
        return 'unknown'

    @staticmethod
    def _get_git_branch():
        """获取当前 Git 分支（不可用时返回 None）"""
        # 方式一：subprocess 调用 git
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=str(settings.BASE_DIR),
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                if branch:
                    return branch
        except (OSError, subprocess.SubprocessError):
            pass

        # 方式二：读取 .git/HEAD
        try:
            git_head = settings.BASE_DIR / '.git' / 'HEAD'
            if git_head.exists():
                content = git_head.read_text(encoding='utf-8').strip()
                # 形如 ref: refs/heads/main
                if content.startswith('ref:'):
                    return content.split('/')[-1]
                return content[:8]
        except OSError:
            pass
        return None

    @extend_schema(
        responses={
            200: success_response_schema(
                'SystemInfoResponse',
                inline_serializer(
                    name='SystemInfoData',
                    fields={
                        'version': serializers.CharField(),
                        'git_branch': serializers.CharField(allow_null=True),
                        'django_version': serializers.CharField(),
                        'python_version': serializers.CharField(),
                        'installed_apps_count': serializers.IntegerField(),
                        'business_apps_count': serializers.IntegerField(),
                        'debug': serializers.BooleanField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        """获取系统信息"""
        import django

        # 业务应用数量（排除 Django 内置及第三方框架应用）
        built_in_prefixes = (
            'django.', 'rest_framework', 'corsheaders',
            'django_filters', 'django_celery',
        )
        business_apps = [
            app for app in settings.INSTALLED_APPS
            if not app.startswith(built_in_prefixes) and app != 'debug_toolbar'
        ]

        data = {
            'version': self._read_version(),
            'git_branch': self._get_git_branch(),
            'django_version': django.get_version(),
            'python_version': '{}.{}.{}'.format(*__import__('sys').version_info[:3]),
            'installed_apps_count': len(settings.INSTALLED_APPS),
            'business_apps_count': len(business_apps),
            'debug': settings.DEBUG,
        }
        return success_response(data, message='success')
