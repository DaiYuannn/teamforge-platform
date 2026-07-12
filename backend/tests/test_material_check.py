"""
N55 材料检查测试
- 检查清单、状态(complete/incomplete/missing)、总体状态
"""
import pytest
from decimal import Decimal

from apps.tasks.models import Task
from apps.finance.models import FinanceBudget
from apps.competitions.models import Competition
from apps.projects.models import Project, ProjectMember

MATERIAL_CHECK_URL = '/api/v1/projects/material-check/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestMaterialCheck:
    """材料检查 API 测试"""

    def test_requires_auth(self, api_client, make_project):
        """未认证不可访问"""
        project = make_project()
        resp = api_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        assert resp.status_code == 401

    def test_missing_project_id(self, member_client):
        """缺少 project_id"""
        resp = member_client.get(MATERIAL_CHECK_URL)
        assert resp.status_code in (400, 404)

    def test_project_not_found(self, member_client):
        """项目不存在"""
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id=99999')
        assert resp.status_code in (400, 404)

    def test_checklist_structure(self, member_client, make_project):
        """检查清单结构"""
        project = make_project()
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'checklist' in data
        assert 'overall_status' in data
        assert 'completed_count' in data
        assert 'total_count' in data
        assert data['total_count'] == 6
        # 每个检查项有 key/label/status/detail
        for item in data['checklist']:
            assert 'key' in item
            assert 'label' in item
            assert item['status'] in ['complete', 'incomplete', 'missing']
            assert 'detail' in item

    def test_proposal_check(self, member_client, make_project):
        """立项书检查"""
        # 阶段 < 2 视为未立项
        project = make_project(current_stage=1)
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        proposal = next(i for i in data['checklist'] if i['key'] == 'project_proposal')
        assert proposal['status'] == 'missing'

        # 阶段 >= 2 且有简介
        project.current_stage = Project.Stage.APPROVED
        project.intro = '项目简介内容'
        project.save()
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        proposal = next(i for i in data['checklist'] if i['key'] == 'project_proposal')
        assert proposal['status'] == 'complete'

    def test_budget_check(self, member_client, make_project):
        """预算计划检查"""
        project = make_project()
        # 无经费总表
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        budget = next(i for i in data['checklist'] if i['key'] == 'budget_plan')
        assert budget['status'] == 'missing'

        # 建立经费总表
        FinanceBudget.objects.create(
            project=project, bonus_amount=Decimal('1000'),
        )
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        budget = next(i for i in data['checklist'] if i['key'] == 'budget_plan')
        assert budget['status'] == 'complete'

    def test_tasks_check(self, member_client, make_project, make_task):
        """任务清单检查"""
        project = make_project()
        # 无任务
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        tasks = next(i for i in data['checklist'] if i['key'] == 'task_list')
        assert tasks['status'] == 'missing'

        # 少量任务
        make_task(project=project)
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        tasks = next(i for i in data['checklist'] if i['key'] == 'task_list')
        assert tasks['status'] == 'incomplete'

        # 3个以上任务
        make_task(project=project)
        make_task(project=project)
        make_task(project=project)
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        tasks = next(i for i in data['checklist'] if i['key'] == 'task_list')
        assert tasks['status'] == 'complete'

    def test_members_check(self, member_client, make_project, make_user):
        """团队成员检查"""
        project = make_project()
        # make_project 默认创建 1 个 leader 成员
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        members = next(i for i in data['checklist'] if i['key'] == 'team_members')
        assert members['status'] == 'incomplete'

        # 添加成员
        u = make_user(email='extra@test.com')
        ProjectMember.objects.create(project=project, user=u, role_in_project='participant')
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        members = next(i for i in data['checklist'] if i['key'] == 'team_members')
        assert members['status'] == 'complete'

    def test_competition_check(self, member_client, make_project):
        """比赛报名检查"""
        project = make_project()
        # 无比赛
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        comp = next(i for i in data['checklist'] if i['key'] == 'competition_registration')
        assert comp['status'] == 'missing'

        # 有比赛且有报名日期
        from datetime import date
        Competition.objects.create(
            project=project, name='校赛', level='school',
            register_date=date(2026, 7, 1),
        )
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        comp = next(i for i in data['checklist'] if i['key'] == 'competition_registration')
        assert comp['status'] == 'complete'

    def test_final_report_check(self, member_client, make_project):
        """终稿报告检查"""
        project = make_project()
        # 进行中项目
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        final = next(i for i in data['checklist'] if i['key'] == 'final_report')
        assert final['status'] == 'incomplete'

    def test_all_complete(self, member_client, make_project, make_task, make_user):
        """全部完备的项目"""
        from datetime import date
        project = make_project(
            current_stage=Project.Stage.AWARDED, status='closed',
            intro='项目简介',
        )
        FinanceBudget.objects.create(project=project, bonus_amount=Decimal('5000'))
        for _ in range(4):
            make_task(project=project)
        u = make_user(email='complete@test.com')
        ProjectMember.objects.create(project=project, user=u, role_in_project='participant')
        Competition.objects.create(
            project=project, name='校赛', level='school',
            register_date=date(2026, 7, 1), is_awarded=True,
        )
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 已获奖项目终稿仍可能 incomplete（无文件），所以 overall 不一定是 complete
        # 但 completed_count 应较高
        assert data['completed_count'] >= 5
        assert data['overall_status'] in ['complete', 'incomplete']

    def test_completion_rate(self, member_client, make_project):
        """完成率计算"""
        project = make_project()
        resp = member_client.get(f'{MATERIAL_CHECK_URL}?project_id={project.id}')
        data = extract_data(resp)
        assert 0 <= data['completion_rate'] <= 1
