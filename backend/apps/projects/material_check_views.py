"""
材料检查视图
- MaterialCheckView: 检查项目是否备齐所需材料（立项书、预算计划、任务清单、团队成员、比赛报名、终稿报告）
- 返回检查清单及状态(complete/incomplete/missing)
"""
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget
from apps.competitions.models import Competition
from apps.files.models import FileAsset


# 材料检查项配置：(key, label, 检查函数)
MATERIAL_CHECKS = [
    ('project_proposal', '项目立项书', 'check_proposal'),
    ('budget_plan', '预算计划', 'check_budget'),
    ('task_list', '任务清单', 'check_tasks'),
    ('team_members', '团队成员', 'check_members'),
    ('competition_registration', '比赛报名', 'check_competition'),
    ('final_report', '终稿报告', 'check_final_report'),
]


class MaterialCheckView(APIView):
    """
    材料检查视图
    GET /api/v1/projects/material-check/?project_id=<id>
    检查项目是否备齐所有必需材料
    返回：checklist（含状态 complete/incomplete/missing）、overall_status
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

        result = _check_materials(project)
        return success_response(result, message='材料检查完成')


def _check_materials(project):
    """检查项目材料完备性"""
    checker = MaterialChecker(project)
    checklist = []
    completed_count = 0

    for key, label, method_name in MATERIAL_CHECKS:
        method = getattr(checker, method_name)
        status, detail = method()
        if status == 'complete':
            completed_count += 1
        checklist.append({
            'key': key,
            'label': label,
            'status': status,
            'detail': detail,
        })

    total = len(checklist)
    overall_status = 'complete' if completed_count == total else (
        'incomplete' if completed_count > 0 else 'missing'
    )

    return {
        'project_id': project.id,
        'project_name': project.name,
        'overall_status': overall_status,
        'completed_count': completed_count,
        'total_count': total,
        'completion_rate': round(completed_count / total, 3) if total > 0 else 0,
        'checklist': checklist,
    }


class MaterialChecker:
    """材料检查器"""

    def __init__(self, project):
        self.project = project

    def check_proposal(self):
        """项目立项书：检查项目是否已立项（阶段≥2）且有简介/文件"""
        # 阶段 ≥ APPROVED(2) 视为已立项
        if self.project.current_stage >= Project.Stage.APPROVED:
            # 检查是否有立项书相关文件（名称包含立项/proposal/申请）
            has_file = FileAsset.objects.filter(
                project=self.project,
                name__iregex='立项|proposal|申请|开题|proposal',
            ).exists()
            if has_file:
                return 'complete', '已立项且立项书文件已上传'
            if self.project.intro:
                return 'complete', '已立项且项目简介已填写'
            return 'incomplete', '已立项但缺少立项书文件'
        return 'missing', '项目尚未立项'

    def check_budget(self):
        """预算计划：检查是否建立经费总表"""
        budget = FinanceBudget.objects.filter(project=self.project).first()
        if budget:
            if budget.total_income and budget.total_income > 0:
                return 'complete', f'经费总表已建立，总额 {budget.total_income}'
            return 'incomplete', '经费总表已建立但总额为 0'
        return 'missing', '尚未建立经费总表'

    def check_tasks(self):
        """任务清单：检查是否有任务"""
        task_count = Task.objects.filter(project=self.project).count()
        if task_count >= 3:
            return 'complete', f'已创建 {task_count} 个任务'
        elif task_count > 0:
            return 'incomplete', f'仅创建 {task_count} 个任务，建议补充'
        return 'missing', '尚未创建任何任务'

    def check_members(self):
        """团队成员：检查项目成员数量"""
        member_count = ProjectMember.objects.filter(project=self.project).count()
        if member_count >= 2:
            return 'complete', f'团队共 {member_count} 人'
        elif member_count == 1:
            return 'incomplete', '仅有 1 名成员（负责人），建议补充团队成员'
        return 'missing', '项目尚未添加任何成员'

    def check_competition(self):
        """比赛报名：检查是否有关联的比赛记录"""
        comp_count = Competition.objects.filter(project=self.project).count()
        if comp_count > 0:
            # 检查是否有报名日期
            with_register = Competition.objects.filter(
                project=self.project,
                register_date__isnull=False,
            ).count()
            if with_register > 0:
                return 'complete', f'已报名 {with_register} 项比赛'
            return 'incomplete', f'有 {comp_count} 项比赛记录但未填写报名日期'
        return 'missing', '尚未关联任何比赛'

    def check_final_report(self):
        """终稿报告：检查项目是否已结项/获奖，或有终稿文件"""
        if self.project.current_stage in (Project.Stage.AWARDED, Project.Stage.CLOSED):
            # 检查是否有终稿/结项/报告相关文件
            has_file = FileAsset.objects.filter(
                project=self.project,
                name__iregex='终稿|结项|报告|final|report|总结',
            ).exists()
            if has_file:
                return 'complete', '项目已结项/获奖且终稿文件已上传'
            return 'incomplete', '项目已结项/获奖但缺少终稿文件'
        # 未结项项目：终稿报告状态为 incomplete（进行中）而非 missing
        return 'incomplete', '项目进行中，终稿报告待完成后提交'
