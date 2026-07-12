"""
项目风险预测视图
- RiskPredictionView: 基于逾期任务、预算超支、团队负载、历史模式分析项目风险
- 返回风险评分(0-100)、风险因子列表、改进建议
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget, FinanceExpense
from apps.competitions.models import Competition
from apps.projects.risk_models import ProjectRisk


class RiskPredictionView(APIView):
    """
    项目风险预测视图
    GET /api/v1/projects/risk-prediction/?project_id=<id>
    分析维度：
      - 逾期任务（overdue tasks）
      - 预算超支（budget overrun）
      - 团队负载（team workload）
      - 历史模式（已识别风险、未更新周期）
    返回：risk_score(0-100)、risk_factors、recommendations
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return error_response(message='缺少参数 project_id', code=1001)
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return error_response(message='项目不存在', code=1004)

        result = _predict_risk(project)
        return success_response(result, message='风险预测成功')


def _predict_risk(project):
    """计算项目风险评分与风险因子"""
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    factors = []

    # ---------- 1. 逾期任务风险 ----------
    tasks = Task.objects.filter(project=project)
    total_tasks = tasks.count()
    overdue_tasks = tasks.filter(status=Task.Status.OVERDUE).count()
    # 即将到期（3天内）且未完成
    soon_deadline = now + timedelta(days=3)
    upcoming_tasks = tasks.filter(
        deadline__lte=soon_deadline,
        deadline__gte=now,
        status__in=[Task.Status.TODO, Task.Status.DOING, Task.Status.PENDING_REVIEW],
    ).count()

    if total_tasks > 0:
        overdue_ratio = overdue_tasks / total_tasks
    else:
        overdue_ratio = 0
    overdue_score = min(overdue_ratio * 100, 40)  # 最多贡献 40 分
    if overdue_tasks > 0:
        factors.append({
            'category': 'overdue_tasks',
            'label': '逾期任务',
            'severity': 'high' if overdue_ratio > 0.3 else 'medium',
            'score': round(overdue_score, 1),
            'detail': f'共 {overdue_tasks} 个逾期任务，即将到期 {upcoming_tasks} 个，任务总数 {total_tasks}',
        })

    # ---------- 2. 预算超支风险 ----------
    budget = FinanceBudget.objects.filter(project=project).first()
    budget_score = 0
    if budget:
        total_income = budget.total_income
        used = budget.used_amount
        if total_income and total_income > 0:
            utilization = float(used) / float(total_income)
            if utilization >= 1.0:
                budget_score = 25
            elif utilization >= 0.9:
                budget_score = 18
            elif utilization >= 0.8:
                budget_score = 12
            if budget_score > 0:
                factors.append({
                    'category': 'budget_overrun',
                    'label': '预算超支',
                    'severity': 'critical' if utilization >= 1.0 else 'high',
                    'score': float(budget_score),
                    'detail': f'经费使用率 {utilization * 100:.1f}%（已用 {used} / 总额 {total_income}）',
                })
            # 经费状态异常
            if budget.status == FinanceBudget.Status.ABNORMAL:
                budget_score = max(budget_score, 20)
                factors.append({
                    'category': 'budget_status',
                    'label': '经费状态异常',
                    'severity': 'high',
                    'score': 20.0,
                    'detail': '经费总表状态为异常',
                })

    # ---------- 3. 团队负载风险 ----------
    members = ProjectMember.objects.filter(project=project)
    member_count = members.count()
    overloaded_members = 0
    if member_count > 0:
        for member in members:
            # 统计该成员在所有项目中的进行中任务数
            active_tasks = Task.objects.filter(
                assignee=member.user,
                status__in=[Task.Status.TODO, Task.Status.DOING, Task.Status.PENDING_REVIEW, Task.Status.NEED_HELP],
            ).count()
            if active_tasks >= 8:
                overloaded_members += 1
        overload_ratio = overloaded_members / member_count
        workload_score = min(overload_ratio * 25, 20)
        if workload_score > 0:
            factors.append({
                'category': 'team_workload',
                'label': '团队负载过高',
                'severity': 'high' if overload_ratio > 0.5 else 'medium',
                'score': round(workload_score, 1),
                'detail': f'{overloaded_members}/{member_count} 名成员任务负载过高（进行中任务≥8）',
            })
    else:
        # 无成员
        factors.append({
            'category': 'no_members',
            'label': '团队为空',
            'severity': 'critical',
            'score': 15.0,
            'detail': '项目尚未添加任何成员',
        })

    # ---------- 4. 历史模式 / 未更新风险 ----------
    # 超过 7 天未打卡
    stale = (
        project.last_leader_update is None
        or project.last_leader_update < week_ago
    )
    if stale:
        factors.append({
            'category': 'stale_update',
            'label': '项目长期未更新',
            'severity': 'medium',
            'score': 10.0,
            'detail': '项目负责人已超过 7 天未更新项目',
        })

    # 已识别的未关闭高风险
    open_high_risks = ProjectRisk.objects.filter(
        project=project,
        status=ProjectRisk.Status.OPEN,
        level__in=[ProjectRisk.Level.HIGH, ProjectRisk.Level.CRITICAL],
    ).count()
    if open_high_risks > 0:
        risk_score = min(open_high_risks * 5, 15)
        factors.append({
            'category': 'open_risks',
            'label': '存在未关闭的高风险',
            'severity': 'high',
            'score': float(risk_score),
            'detail': f'共有 {open_high_risks} 个未关闭的高级别风险',
        })

    # ---------- 汇总风险评分（0-100，越高越危险）----------
    total_score = min(sum(f['score'] for f in factors), 100)

    # ---------- 改进建议 ----------
    recommendations = _build_recommendations(factors, project)

    return {
        'project_id': project.id,
        'project_name': project.name,
        'risk_score': round(total_score, 1),
        'risk_level': _risk_level(total_score),
        'risk_factors': factors,
        'recommendations': recommendations,
        'analyzed_at': now.isoformat(),
    }


def _risk_level(score):
    """将评分映射为风险级别"""
    if score >= 70:
        return 'critical'
    elif score >= 45:
        return 'high'
    elif score >= 25:
        return 'medium'
    return 'low'


def _build_recommendations(factors, project):
    """根据风险因子生成改进建议"""
    recs = []
    categories = {f['category'] for f in factors}

    if 'overdue_tasks' in categories:
        recs.append('尽快处理逾期任务，必要时调整任务截止时间或重新分配负责人。')
    if 'budget_overrun' in categories or 'budget_status' in categories:
        recs.append('审查经费使用情况，控制支出并申请追加预算或调整开支计划。')
    if 'team_workload' in categories:
        recs.append('均衡团队成员任务分配，避免单点过载，必要时增派人手。')
    if 'no_members' in categories:
        recs.append('尽快为项目添加成员，明确分工。')
    if 'stale_update' in categories:
        recs.append('项目负责人应定期打卡更新项目进展，保持信息同步。')
    if 'open_risks' in categories:
        recs.append('针对未关闭的高风险制定缓解措施并跟踪关闭。')

    if not recs:
        recs.append('项目风险较低，继续保持当前进度管理与风险监控。')
    return recs
