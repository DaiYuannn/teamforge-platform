"""
智能周报视图
- WeeklyReportView: 自动生成周报（完成任务、新增任务、待办事项、项目进度、即将到期、团队动态）
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from common.permissions import IsInternalTeamMember
from common.response import success_response
from common.schema import success_response_schema
from apps.projects.models import Project, ProjectStageLog
from apps.tasks.models import Task
from apps.finance.models import FinanceExpense
from apps.competitions.models import Competition
from apps.contributions.models import Contribution


class WeeklyReportSummarySerializer(serializers.Serializer):
    report_period_start = serializers.DateTimeField()
    report_period_end = serializers.DateTimeField()
    weeks = serializers.IntegerField()
    tasks_completed = serializers.IntegerField()
    tasks_new = serializers.IntegerField()
    tasks_pending = serializers.IntegerField()
    tasks_overdue = serializers.IntegerField()
    tasks_upcoming_deadline = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    stage_changes = serializers.IntegerField()
    weekly_expense = serializers.FloatField()
    team_activities = serializers.IntegerField()


class WeeklyReportTaskSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    project_id = serializers.IntegerField()
    project_name = serializers.CharField(allow_blank=True)
    assignee_id = serializers.IntegerField(allow_null=True)
    assignee_name = serializers.CharField(allow_blank=True)
    deadline = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)


class WeeklyProjectProgressSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    project_code = serializers.CharField()
    current_stage = serializers.CharField()
    current_stage_display = serializers.CharField()
    tasks_completed_this_week = serializers.IntegerField()
    tasks_new_this_week = serializers.IntegerField()
    last_update = serializers.DateTimeField(allow_null=True)


class WeeklyStageChangeSerializer(serializers.Serializer):
    project_name = serializers.CharField(allow_blank=True)
    from_stage = serializers.CharField()
    to_stage = serializers.CharField(allow_blank=True)
    operator = serializers.CharField()
    date = serializers.DateTimeField(allow_null=True)


class WeeklyCompetitionEventSerializer(serializers.Serializer):
    field = serializers.CharField()
    label = serializers.CharField()
    date = serializers.DateField()


class WeeklyCompetitionSerializer(serializers.Serializer):
    competition_id = serializers.IntegerField()
    competition_name = serializers.CharField()
    level = serializers.CharField()
    level_display = serializers.CharField()
    project_name = serializers.CharField(allow_blank=True)
    events = WeeklyCompetitionEventSerializer(many=True)


class WeeklyTeamActivitySerializer(serializers.Serializer):
    user_id = serializers.IntegerField(allow_null=True)
    user_name = serializers.CharField(allow_blank=True)
    project_id = serializers.IntegerField(allow_null=True)
    project_name = serializers.CharField(allow_blank=True)
    contribution_type = serializers.CharField()
    content = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class WeeklyReportDataSerializer(serializers.Serializer):
    summary = WeeklyReportSummarySerializer()
    narrative = serializers.CharField()
    completed_tasks = WeeklyReportTaskSerializer(many=True)
    new_tasks = WeeklyReportTaskSerializer(many=True)
    pending_tasks = WeeklyReportTaskSerializer(many=True)
    overdue_tasks = WeeklyReportTaskSerializer(many=True)
    upcoming_deadline_tasks = WeeklyReportTaskSerializer(many=True)
    project_progress = WeeklyProjectProgressSerializer(many=True)
    stage_changes = WeeklyStageChangeSerializer(many=True)
    upcoming_competitions = WeeklyCompetitionSerializer(many=True)
    team_activity = WeeklyTeamActivitySerializer(many=True)


class WeeklyReportView(APIView):
    """
    智能周报视图
    GET /api/v1/dashboard/weekly-report/
    可选参数：
      - project_id: 按项目过滤
      - weeks: 回溯周数（默认 1）
    自动生成周报：完成任务、新增任务、待办事项、项目进度、即将到期、团队动态
    """

    permission_classes = [IsInternalTeamMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='project_id', type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='weeks', type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, default=1,
                description='Number of weeks to include; values below 1 become 1.',
            ),
        ],
        responses={
            200: success_response_schema(
                'WeeklyReportResponse', WeeklyReportDataSerializer(),
            ),
        },
    )
    def get(self, request):
        project_id = request.query_params.get('project_id')
        weeks = request.query_params.get('weeks', '1')
        try:
            weeks = max(int(weeks), 1)
        except (TypeError, ValueError):
            weeks = 1

        now = timezone.now()
        start = now - timedelta(weeks=weeks)

        result = _build_weekly_report(now, start, project_id, weeks)
        return success_response(result, message='周报生成成功')


def _build_weekly_report(now, start, project_id, weeks):
    """构建周报数据"""
    # ---------- 任务统计 ----------
    task_qs = Task.objects.all()
    if project_id:
        task_qs = task_qs.filter(project_id=project_id)

    completed_tasks = task_qs.filter(
        status=Task.Status.DONE,
        completed_at__range=(start, now),
    ).select_related('project', 'assignee')
    new_tasks = task_qs.filter(created_at__range=(start, now)).select_related(
        'project', 'assignee'
    )
    pending_tasks = task_qs.filter(
        status__in=[Task.Status.TODO, Task.Status.DOING, Task.Status.PENDING_REVIEW],
    ).select_related('project', 'assignee')

    # 即将到期（7天内）
    soon = now + timedelta(days=7)
    upcoming_deadline = task_qs.filter(
        deadline__gte=now,
        deadline__lte=soon,
        status__in=[Task.Status.TODO, Task.Status.DOING, Task.Status.PENDING_REVIEW],
    ).select_related('project', 'assignee').order_by('deadline')

    # 逾期任务
    overdue_tasks = task_qs.filter(status=Task.Status.OVERDUE).select_related(
        'project', 'assignee'
    )

    # ---------- 项目进度 ----------
    project_qs = Project.objects.all()
    if project_id:
        project_qs = project_qs.filter(id=project_id)
    active_projects = project_qs.filter(status=Project.Status.ACTIVE)

    # 阶段变更（本周）
    stage_changes = ProjectStageLog.objects.filter(
        created_at__range=(start, now)
    ).select_related('project', 'operator')
    if project_id:
        stage_changes = stage_changes.filter(project_id=project_id)

    stage_choices = dict(Project.Stage.choices)
    project_progress = []
    for project in active_projects:
        # 本周完成/新增任务数
        proj_done = completed_tasks.filter(project=project).count()
        proj_new = new_tasks.filter(project=project).count()
        project_progress.append({
            'project_id': project.id,
            'project_name': project.name,
            'project_code': project.code,
            'current_stage': project.current_stage,
            'current_stage_display': project.get_current_stage_display(),
            'tasks_completed_this_week': proj_done,
            'tasks_new_this_week': proj_new,
            'last_update': project.last_leader_update.isoformat() if project.last_leader_update else None,
        })

    # ---------- 经费支出（本周）----------
    expense_qs = FinanceExpense.objects.filter(expense_date__range=(
        start.date(), now.date()
    ))
    if project_id:
        expense_qs = expense_qs.filter(project_id=project_id)
    weekly_expense = expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # ---------- 比赛动态（本周内有节点的比赛）----------
    comp_qs = Competition.objects.all()
    if project_id:
        comp_qs = comp_qs.filter(project_id=project_id)
    upcoming_competitions = []
    for comp in comp_qs:
        # 检查本周内是否有报名/材料/答辩/结果节点
        events = []
        for field, label in [
            ('register_date', '报名截止'),
            ('material_deadline', '材料截止'),
            ('defense_date', '答辩'),
            ('result_date', '结果公布'),
        ]:
            val = getattr(comp, field, None)
            if val and start.date() <= val <= now.date() + timedelta(days=14):
                events.append({'field': field, 'label': label, 'date': val.isoformat()})
        if events:
            upcoming_competitions.append({
                'competition_id': comp.id,
                'competition_name': comp.name,
                'level': comp.level,
                'level_display': comp.get_level_display(),
                'project_name': comp.project.name if comp.project else '',
                'events': events,
            })

    # ---------- 团队动态（本周贡献记录）----------
    contrib_qs = Contribution.objects.filter(created_at__range=(start, now))
    if project_id:
        contrib_qs = contrib_qs.filter(project_id=project_id)
    contrib_count = contrib_qs.count()
    team_activity = []
    for contrib in contrib_qs.select_related('user', 'project')[:50]:
        team_activity.append({
            'user_id': contrib.user_id,
            'user_name': contrib.user.name if contrib.user else '',
            'project_id': contrib.project_id,
            'project_name': contrib.project.name if contrib.project else '',
            'contribution_type': contrib.contribution_type,
            'content': contrib.content[:100] if contrib.content else '',
            'created_at': contrib.created_at.isoformat(),
        })

    # ---------- 汇总 ----------
    summary = {
        'report_period_start': start.isoformat(),
        'report_period_end': now.isoformat(),
        'weeks': weeks,
        'tasks_completed': completed_tasks.count(),
        'tasks_new': new_tasks.count(),
        'tasks_pending': pending_tasks.count(),
        'tasks_overdue': overdue_tasks.count(),
        'tasks_upcoming_deadline': upcoming_deadline.count(),
        'active_projects': active_projects.count(),
        'stage_changes': stage_changes.count(),
        'weekly_expense': float(weekly_expense),
        'team_activities': contrib_count,
    }

    # 周报正文
    narrative = _build_narrative(summary)

    return {
        'summary': summary,
        'narrative': narrative,
        'completed_tasks': _task_list(completed_tasks),
        'new_tasks': _task_list(new_tasks),
        'pending_tasks': _task_list(pending_tasks),
        'overdue_tasks': _task_list(overdue_tasks),
        'upcoming_deadline_tasks': _task_list(upcoming_deadline),
        'project_progress': project_progress,
        'stage_changes': [
            {
                'project_name': sc.project.name if sc.project else '',
                'from_stage': stage_choices.get(sc.from_stage, '初始') if sc.from_stage else '初始',
                'to_stage': stage_choices.get(sc.to_stage, ''),
                'operator': sc.operator.name if sc.operator else '系统',
                'date': sc.created_at.isoformat() if sc.created_at else None,
            }
            for sc in stage_changes
        ],
        'upcoming_competitions': upcoming_competitions,
        'team_activity': team_activity,
    }


def _task_list(qs):
    """将任务 queryset 序列化为列表"""
    return [
        {
            'task_id': t.id,
            'title': t.title,
            'status': t.status,
            'status_display': t.get_status_display(),
            'project_id': t.project_id,
            'project_name': t.project.name if t.project else '',
            'assignee_id': t.assignee_id,
            'assignee_name': t.assignee.name if t.assignee else '',
            'deadline': t.deadline.isoformat() if t.deadline else None,
            'completed_at': t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in qs[:100]
    ]


def _build_narrative(summary):
    """生成周报叙述文本"""
    parts = []
    parts.append(
        f'本周（{summary["report_period_start"][:10]} 至 {summary["report_period_end"][:10]}）'
    )
    parts.append(f'共完成任务 {summary["tasks_completed"]} 个，新增任务 {summary["tasks_new"]} 个。')
    parts.append(
        f'当前待办任务 {summary["tasks_pending"]} 个，其中逾期 {summary["tasks_overdue"]} 个，'
        f'即将到期 {summary["tasks_upcoming_deadline"]} 个。'
    )
    parts.append(
        f'活跃项目 {summary["active_projects"]} 个，本周发生阶段变更 {summary["stage_changes"]} 次。'
    )
    parts.append(f'本周经费支出合计 {summary["weekly_expense"]:.2f} 元。')
    parts.append(f'团队共产生 {summary["team_activities"]} 条动态记录。')
    return ''.join(parts)
