"""
项目健康度评分视图
- ProjectHealthScoreView: 基于任务完成率、进度合规、经费使用、团队参与、风险状态计算项目健康度
- 返回总分(0-100)、分类评分、等级(A/B/C/D)
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.permissions import IsInternalTeamMember
from common.schema import success_response_schema
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget
from apps.projects.risk_models import ProjectRisk


class ProjectHealthScoreView(APIView):
    """
    项目健康度评分视图
    GET /api/v1/projects/health-score/?project_id=<id>
    评分维度（权重）：
      - 任务完成率（30%）
      - 进度合规（20%）
      - 经费使用（20%）
      - 团队参与（15%）
      - 风险状态（15%）
    返回：overall_score(0-100)、category_scores、grade(A/B/C/D)
    """

    # 评分包含经费状态，外部协作者和已离队账号不得通过聚合结果旁路读取。
    permission_classes = [IsInternalTeamMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='project_id',
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description='待评分的项目 ID。',
            ),
        ],
        responses={
            200: success_response_schema(
                'ProjectHealthScoreResponse',
                inline_serializer(
                    name='ProjectHealthScoreData',
                    fields={
                        'project_id': serializers.IntegerField(),
                        'project_name': serializers.CharField(),
                        'overall_score': serializers.FloatField(),
                        'grade': serializers.ChoiceField(choices=['A', 'B', 'C', 'D']),
                        'category_scores': serializers.DictField(
                            child=inline_serializer(
                                name='ProjectHealthCategoryScore',
                                fields={
                                    'label': serializers.CharField(),
                                    'score': serializers.FloatField(),
                                    'weight': serializers.FloatField(),
                                    'detail': serializers.CharField(),
                                },
                            ),
                        ),
                        'analyzed_at': serializers.DateTimeField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return error_response(message='缺少参数 project_id', code=1001)
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return error_response(message='项目不存在', code=1004)

        result = _compute_health_score(project)
        return success_response(result, message='健康度评分成功')


def _compute_health_score(project):
    """计算项目健康度评分"""
    now = timezone.now()
    category_scores = {}

    # ---------- 1. 任务完成率（30%）----------
    tasks = Task.objects.filter(project=project)
    total_tasks = tasks.count()
    done_tasks = tasks.filter(status=Task.Status.DONE).count()
    if total_tasks > 0:
        completion_rate = done_tasks / total_tasks
    else:
        completion_rate = 1.0  # 无任务视为满分
    task_score = round(completion_rate * 100, 1)
    category_scores['task_completion'] = {
        'label': '任务完成率',
        'score': task_score,
        'weight': 0.30,
        'detail': f'已完成 {done_tasks}/{total_tasks}（{completion_rate * 100:.1f}%）',
    }

    # ---------- 2. 进度合规（20%）----------
    schedule_score = _schedule_score(project, now)
    category_scores['schedule_adherence'] = {
        'label': '进度合规',
        'score': schedule_score,
        'weight': 0.20,
        'detail': _schedule_detail(project),
    }

    # ---------- 3. 经费使用（20%）----------
    budget_score, budget_detail = _budget_score(project)
    category_scores['budget_utilization'] = {
        'label': '经费使用',
        'score': budget_score,
        'weight': 0.20,
        'detail': budget_detail,
    }

    # ---------- 4. 团队参与（15%）----------
    member_count = ProjectMember.objects.filter(
        project=project, status=ProjectMember.Status.ACTIVE
    ).count()
    week_ago = now - timedelta(days=7)
    recent_tasks = tasks.filter(created_at__gte=week_ago).count()
    # 团队规模与近期活跃度
    if member_count == 0:
        engagement_score = 0.0
        engagement_detail = '项目无成员'
    else:
        # 成员越多得分越高（封顶），近期有任务活动加分
        size_score = min(member_count / 5 * 60, 60)
        activity_score = min(recent_tasks * 10, 40)
        engagement_score = round(size_score + activity_score, 1)
        engagement_detail = f'成员 {member_count} 人，近 7 天新增任务 {recent_tasks} 个'
    category_scores['team_engagement'] = {
        'label': '团队参与',
        'score': engagement_score,
        'weight': 0.15,
        'detail': engagement_detail,
    }

    # ---------- 5. 风险状态（15%）----------
    open_risks = ProjectRisk.objects.filter(
        project=project, status=ProjectRisk.Status.OPEN
    ).count()
    critical_risks = ProjectRisk.objects.filter(
        project=project,
        status=ProjectRisk.Status.OPEN,
        level=ProjectRisk.Level.CRITICAL,
    ).count()
    if open_risks == 0:
        risk_score = 100.0
    else:
        # 严重风险扣分多
        risk_score = max(100 - open_risks * 10 - critical_risks * 15, 0)
    category_scores['risk_status'] = {
        'label': '风险状态',
        'score': float(risk_score),
        'weight': 0.15,
        'detail': f'开放风险 {open_risks} 个（其中严重 {critical_risks} 个）',
    }

    # ---------- 总分 ----------
    overall = sum(
        cs['score'] * cs['weight'] for cs in category_scores.values()
    )
    overall = round(overall, 1)
    grade = _grade(overall)

    return {
        'project_id': project.id,
        'project_name': project.name,
        'overall_score': overall,
        'grade': grade,
        'category_scores': category_scores,
        'analyzed_at': now.isoformat(),
    }


def _schedule_score(project, now):
    """进度合规评分"""
    # 已关闭/已获奖项目视为满分
    if project.status == Project.Status.CLOSED or project.current_stage == Project.Stage.AWARDED:
        return 100.0
    # 有计划结束日期：判断是否逾期
    if project.planned_end_date:
        planned_end = project.planned_end_date
        today = now.date()
        if today <= planned_end:
            # 未到截止日期，按阶段进度给分
            stage_ratio = min(project.current_stage / 13, 1.0)
            return round(60 + stage_ratio * 40, 1)
        else:
            # 逾期：按逾期天数扣分
            overdue_days = (today - planned_end).days
            return max(100 - overdue_days * 2, 0)
    # 无计划结束日期：按阶段进度
    stage_ratio = min(project.current_stage / 13, 1.0)
    return round(stage_ratio * 100, 1)


def _schedule_detail(project):
    """进度合规说明"""
    if project.status == Project.Status.CLOSED:
        return '项目已关闭，进度满分'
    if project.current_stage == Project.Stage.AWARDED:
        return '项目已获奖，进度满分'
    if project.planned_end_date:
        return f'当前阶段 {project.get_current_stage_display()}，计划结束 {project.planned_end_date}'
    return f'当前阶段 {project.get_current_stage_display()}，未设置计划结束日期'


def _budget_score(project):
    """经费使用评分"""
    budget = FinanceBudget.objects.filter(project=project).first()
    if not budget:
        return 80.0, '未建立经费总表，按默认评分'
    total_income = budget.total_income
    used = budget.used_amount
    if not total_income or total_income <= 0:
        return 70.0, '经费总额为 0'
    utilization = float(used) / float(total_income)
    # 使用率在 50%-90% 为健康
    if budget.status == FinanceBudget.Status.ABNORMAL:
        return 30.0, f'经费状态异常，使用率 {utilization * 100:.1f}%'
    if budget.status == FinanceBudget.Status.WARNING:
        return 60.0, f'经费状态预警，使用率 {utilization * 100:.1f}%'
    if utilization > 1.0:
        return 40.0, f'经费超支，使用率 {utilization * 100:.1f}%'
    if 0.5 <= utilization <= 0.9:
        return 100.0, f'经费使用健康，使用率 {utilization * 100:.1f}%'
    if utilization < 0.5:
        return 80.0, f'经费使用偏低，使用率 {utilization * 100:.1f}%'
    return 70.0, f'经费使用偏高，使用率 {utilization * 100:.1f}%'


def _grade(score):
    """将评分映射为等级"""
    if score >= 90:
        return 'A'
    elif score >= 75:
        return 'B'
    elif score >= 60:
        return 'C'
    return 'D'
