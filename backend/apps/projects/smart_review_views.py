"""
智能复盘视图
- SmartReviewView: 基于项目数据自动生成复盘建议（成果、问题、时间线、团队表现）
- 可作为 M09 ProjectReview 的起点
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.permissions import IsInternalTeamMember
from apps.projects.models import Project, ProjectMember, ProjectStageLog
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget, FinanceExpense
from apps.competitions.models import Competition
from apps.projects.risk_models import ProjectRisk
from apps.contributions.models import Contribution


class SmartReviewView(APIView):
    """
    智能复盘视图
    GET /api/v1/projects/smart-review/?project_id=<id>
    自动生成复盘建议：成果总结、问题领域、时间线分析、团队表现
    """

    # 智能复盘会返回经费汇总，必须与财务模块保持同一内部数据域。
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return error_response(message='缺少参数 project_id', code=1001)
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return error_response(message='项目不存在', code=1004)

        result = _generate_smart_review(project)
        return success_response(result, message='智能复盘生成成功')


def _generate_smart_review(project):
    """生成智能复盘内容"""
    now = timezone.now()

    # ---------- 任务统计 ----------
    tasks = Task.objects.filter(project=project)
    total_tasks = tasks.count()
    done_tasks = tasks.filter(status=Task.Status.DONE).count()
    overdue_tasks = tasks.filter(status=Task.Status.OVERDUE).count()
    cancelled_tasks = tasks.filter(status=Task.Status.CANCELLED).count()
    completion_rate = (done_tasks / total_tasks) if total_tasks > 0 else 0

    # ---------- 经费统计 ----------
    budget = FinanceBudget.objects.filter(project=project).first()
    expenses = FinanceExpense.objects.filter(project=project)
    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    finance_summary = {
        'has_budget': budget is not None,
        'total_expense': float(total_expense),
        'expense_count': expenses.count(),
    }
    if budget:
        finance_summary['total_income'] = float(budget.total_income)
        finance_summary['used_amount'] = float(budget.used_amount)
        finance_summary['utilization'] = (
            float(budget.used_amount) / float(budget.total_income)
            if budget.total_income else 0
        )

    # ---------- 比赛成果 ----------
    competitions = Competition.objects.filter(project=project)
    awarded_competitions = competitions.filter(is_awarded=True)
    achievements = []
    for comp in awarded_competitions:
        achievements.append({
            'competition_name': comp.name,
            'level': comp.level,
            'level_display': comp.get_level_display(),
            'award_level': comp.award_level,
        })

    # ---------- 团队表现 ----------
    members = ProjectMember.objects.filter(
        project=project, status=ProjectMember.Status.ACTIVE
    ).select_related('user')
    team_performance = []
    for member in members:
        member_tasks = tasks.filter(assignee=member.user)
        member_done = member_tasks.filter(status=Task.Status.DONE).count()
        member_total = member_tasks.count()
        contributions = Contribution.objects.filter(
            user=member.user, project=project
        ).count()
        team_performance.append({
            'user_id': member.user.id,
            'user_name': member.user.name,
            'role_in_project': member.role_in_project,
            'task_total': member_total,
            'task_done': member_done,
            'contribution_count': contributions,
            'completion_rate': round(member_done / member_total, 2) if member_total > 0 else 0,
        })

    # ---------- 问题领域 ----------
    problem_areas = []
    if overdue_tasks > 0:
        problem_areas.append({
            'area': 'task_overdue',
            'label': '任务逾期',
            'detail': f'共 {overdue_tasks} 个任务逾期',
        })
    if budget and budget.total_income and budget.used_amount > budget.total_income:
        problem_areas.append({
            'area': 'budget_overrun',
            'label': '经费超支',
            'detail': f'已用 {budget.used_amount} 超过总额 {budget.total_income}',
        })
    open_risks = ProjectRisk.objects.filter(
        project=project, status=ProjectRisk.Status.OPEN
    ).count()
    if open_risks > 0:
        problem_areas.append({
            'area': 'open_risks',
            'label': '未关闭风险',
            'detail': f'共 {open_risks} 个未关闭风险',
        })
    update_baseline = project.last_leader_update or project.created_at
    stale = update_baseline <= now - timedelta(days=11)
    if stale:
        problem_areas.append({
            'area': 'stale_update',
            'label': '更新滞后',
            'detail': '项目负责人超过 11 天未更新',
        })
    if completion_rate < 0.5 and total_tasks > 0:
        problem_areas.append({
            'area': 'low_completion',
            'label': '任务完成率低',
            'detail': f'完成率仅 {completion_rate * 100:.1f}%',
        })

    # ---------- 时间线分析 ----------
    stage_logs = ProjectStageLog.objects.filter(project=project).order_by('created_at')
    stage_choices = dict(Project.Stage.choices)
    timeline = []
    for log in stage_logs:
        timeline.append({
            'from_stage': stage_choices.get(log.from_stage, '初始') if log.from_stage else '初始',
            'to_stage': stage_choices.get(log.to_stage, ''),
            'date': log.created_at.isoformat() if log.created_at else None,
            'note': log.note,
        })
    # 关键节点：比赛答辩、获奖
    for comp in competitions:
        if comp.defense_date:
            timeline.append({
                'event': 'defense',
                'label': f'{comp.name} 答辩',
                'date': comp.defense_date.isoformat(),
            })
        if comp.is_awarded and comp.result_date:
            timeline.append({
                'event': 'awarded',
                'label': f'{comp.name} 获奖（{comp.award_level}）',
                'date': comp.result_date.isoformat(),
            })
    # 按日期排序
    timeline.sort(key=lambda x: x.get('date') or '')

    # ---------- 自动生成的总结文本 ----------
    summary = _build_summary(
        project, total_tasks, done_tasks, completion_rate,
        finance_summary, achievements, problem_areas
    )
    lessons = _build_lessons(problem_areas)
    improvements = _build_improvements(problem_areas)

    return {
        'project_id': project.id,
        'project_name': project.name,
        'generated_at': now.isoformat(),
        'summary': summary,
        'achievements': achievements,
        'problem_areas': problem_areas,
        'lessons': lessons,
        'improvements': improvements,
        'task_statistics': {
            'total': total_tasks,
            'done': done_tasks,
            'overdue': overdue_tasks,
            'cancelled': cancelled_tasks,
            'completion_rate': round(completion_rate, 3),
        },
        'finance_summary': finance_summary,
        'team_performance': team_performance,
        'timeline': timeline,
    }


def _build_summary(project, total_tasks, done_tasks, completion_rate,
                   finance_summary, achievements, problem_areas):
    """生成项目总结文本"""
    parts = []
    parts.append(f'项目"{project.name}"当前处于"{project.get_current_stage_display()}"阶段。')
    if total_tasks > 0:
        parts.append(f'共创建任务 {total_tasks} 个，已完成 {done_tasks} 个，完成率 {completion_rate * 100:.1f}%。')
    if achievements:
        parts.append(f'项目共获得 {len(achievements)} 项比赛奖励。')
    if finance_summary.get('has_budget'):
        util = finance_summary.get('utilization', 0)
        parts.append(f'经费使用率为 {util * 100:.1f}%。')
    if problem_areas:
        parts.append(f'存在 {len(problem_areas)} 个需要关注的问题领域。')
    return ''.join(parts)


def _build_lessons(problem_areas):
    """生成经验教训"""
    lessons = []
    for p in problem_areas:
        if p['area'] == 'task_overdue':
            lessons.append('任务时间管理需加强，应合理评估任务工作量并预留缓冲期。')
        elif p['area'] == 'budget_overrun':
            lessons.append('经费预算应预留余量，重大支出前需严格审批。')
        elif p['area'] == 'open_risks':
            lessons.append('风险识别后需及时制定缓解措施并跟踪关闭。')
        elif p['area'] == 'stale_update':
            lessons.append('应建立定期更新机制，保持项目信息同步。')
        elif p['area'] == 'low_completion':
            lessons.append('任务推进节奏需加快，及时清理阻塞任务。')
    if not lessons:
        lessons.append('项目整体推进顺利，建议持续保持良好的管理实践。')
    return lessons


def _build_improvements(problem_areas):
    """生成改进建议"""
    improvements = []
    for p in problem_areas:
        if p['area'] == 'task_overdue':
            improvements.append('建立任务预警机制，对临近截止的任务提前介入。')
        elif p['area'] == 'budget_overrun':
            improvements.append('制定详细的经费使用计划，按月度审核预算执行情况。')
        elif p['area'] == 'open_risks':
            improvements.append('每周复盘风险清单，指定责任人推动关闭。')
        elif p['area'] == 'stale_update':
            improvements.append('引入每周打卡制度，负责人需定期同步进展。')
        elif p['area'] == 'low_completion':
            improvements.append('拆分大任务为可量化的小任务，提高可见度与推进效率。')
    if not improvements:
        improvements.append('继续保持现有管理节奏，可在复盘与知识沉淀方面进一步加强。')
    return improvements
