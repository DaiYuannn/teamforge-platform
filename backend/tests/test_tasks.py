"""
任务 API 测试 - 验证 P01 修复
- priority 字段
- start_date 字段
- CRUD 操作
"""
from io import BytesIO

import openpyxl
import pytest
from django.utils import timezone


@pytest.mark.api
@pytest.mark.django_db
class TestTaskAPI:
    """任务 API 测试"""

    def _make_project_for(self, client, make_project):
        """创建以 client.user 为负责人的项目"""
        from apps.projects.models import ProjectMember
        project = make_project(leader=client.user)
        return project

    def test_create_task_with_priority(self, teacher_client, make_project):
        """创建任务时带优先级"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '测试任务-高优先级',
            'assignee': project.leader.id,
            'priority': 'high',
            'deadline': '2026-12-31T23:59:59',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['priority'] == 'high'
        assert data['priority_display'] == '高'

    def test_create_task_default_priority(self, teacher_client, make_project):
        """创建任务默认优先级为 medium"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '测试任务-默认优先级',
            'assignee': project.leader.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['priority'] == 'medium'
        assert data['priority_display'] == '中'

    def test_create_task_with_start_date(self, teacher_client, make_project):
        """创建任务时带开始时间"""
        project = make_project(leader=teacher_client.user)
        start = timezone.now().isoformat()
        resp = teacher_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '测试任务-带开始时间',
            'assignee': project.leader.id,
            'start_date': start,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['start_date'] is not None

    def test_task_list_includes_priority(self, member_client, make_task):
        """任务列表包含 priority 字段"""
        task = make_task(priority='urgent')
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) > 0
        assert 'priority' in results[0]
        assert 'priority_display' in results[0]

    def test_task_list_includes_start_date(self, member_client, make_task):
        """任务列表包含 start_date 字段"""
        task = make_task()
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        assert 'start_date' in results[0]

    def test_filter_by_priority(self, member_client, make_task):
        """按优先级筛选"""
        make_task(priority='low')
        make_task(priority='urgent')
        resp = member_client.get('/api/v1/tasks/?priority=urgent')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        assert all(r['priority'] == 'urgent' for r in results)

    def test_update_task_priority(self, teacher_client, make_project, make_task):
        """更新任务优先级"""
        project = make_project(leader=teacher_client.user)
        task = make_task(project=project, priority='low')
        resp = teacher_client.patch(f'/api/v1/tasks/{task.id}/', {
            'priority': 'urgent',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['priority'] == 'urgent'

    def test_member_cannot_create_task(self, member_client, make_project):
        """普通成员不能创建任务"""
        project = make_project()
        resp = member_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '成员尝试创建任务',
            'assignee': project.leader.id,
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_member_can_view_tasks(self, member_client, make_task):
        """普通成员可以查看任务"""
        make_task()
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200

    def test_task_no_due_date_field(self, member_client, make_task):
        """任务 API 不返回 due_date 字段"""
        task = make_task()
        resp = member_client.get(f'/api/v1/tasks/{task.id}/')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        assert 'due_date' not in data
        assert 'deadline' in data

    def test_task_export_applies_current_list_filters(
        self, member_client, make_project, make_task, make_user,
    ):
        """任务 Excel 导出与页面的项目、状态、优先级、负责人、范围和搜索一致。"""
        project = make_project()
        matching = make_task(
            project=project,
            assignee=member_client.user,
            title='筛选命中任务',
            description='当前导出结果',
            status='doing',
            priority='high',
            completion_note='等待提交审核',
        )
        make_task(
            project=project,
            assignee=member_client.user,
            title='状态不匹配',
            status='todo',
            priority='high',
        )
        make_task(
            project=project,
            assignee=make_user(email='export-other-assignee@test.com'),
            title='负责人不匹配',
            status='doing',
            priority='high',
        )

        response = member_client.get('/api/v1/exports/', {
            'type': 'tasks',
            'file_format': 'xlsx',
            'project_id': project.id,
            'search': '筛选命中',
            'status': 'doing',
            'priority': 'high',
            'assignee': member_client.user.id,
            'scope': 'mine',
        })

        assert response.status_code == 200
        workbook = openpyxl.load_workbook(BytesIO(response.content), read_only=True)
        rows = list(workbook['任务清单'].iter_rows(values_only=True))
        assert rows[0] == (
            '任务标题', '所属项目', '指派给', '协作者', '审核人', '创建者',
            '状态', '优先级', '截止时间', '完成时间', '是否逾期',
            '延期原因', '完成说明', '创建时间',
        )
        assert [row[0] for row in rows[1:]] == [matching.title]


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
class TestTaskProjectPermissions:
    """项目负责人可管理自己的任务，但不能跨项目越权。"""

    def test_project_leader_can_create_update_and_delete_task(
        self, api_client, make_project, make_user,
    ):
        leader = make_user(email='task-leader@test.com')
        project = make_project(leader=leader)
        assignee = make_user(email='task-assignee@test.com')
        api_client.force_authenticate(user=leader)

        create_response = api_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '负责人创建的任务',
            'assignee': assignee.id,
        }, format='json')
        assert create_response.status_code == 201, create_response.json()
        task_id = create_response.json()['data']['id']

        update_response = api_client.patch(
            f'/api/v1/tasks/{task_id}/',
            {'title': '负责人更新的任务'},
            format='json',
        )
        assert update_response.status_code == 200, update_response.json()

        delete_response = api_client.delete(f'/api/v1/tasks/{task_id}/')
        assert delete_response.status_code == 200, delete_response.json()

    def test_member_cannot_create_task_for_another_users_project(
        self, api_client, make_project, make_user,
    ):
        member = make_user(email='task-outsider@test.com')
        project = make_project()
        api_client.force_authenticate(user=member)

        response = api_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '越权创建任务',
            'assignee': member.id,
        }, format='json')

        assert response.status_code == 403

    def test_project_leader_cannot_move_task_to_another_project(
        self, api_client, make_project, make_task, make_user,
    ):
        leader = make_user(email='task-owner@test.com')
        own_project = make_project(leader=leader)
        other_project = make_project()
        task = make_task(project=own_project, creator=leader)
        api_client.force_authenticate(user=leader)

        response = api_client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'project': other_project.id},
            format='json',
        )

        assert response.status_code == 403
        task.refresh_from_db()
        assert task.project_id == own_project.id

    @pytest.mark.parametrize('relation', ['assignee', 'collaborator'])
    def test_task_executors_can_advance_work_to_pending_review(
        self, relation, api_client, make_project, make_task, make_user,
    ):
        operator = make_user(email=f'task-{relation}@test.com')
        project = make_project()
        task_kwargs = {'assignee': operator} if relation == 'assignee' else {}
        task = make_task(project=project, **task_kwargs)
        if relation == 'collaborator':
            task.collaborators.add(operator)
        api_client.force_authenticate(user=operator)

        response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'doing'},
            format='json',
        )

        assert response.status_code == 200, response.json()

        submit_response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'pending_review', 'completion_note': '交付物已上传'},
            format='json',
        )
        assert submit_response.status_code == 200, submit_response.json()
        task.refresh_from_db()
        assert task.status == 'pending_review'
        assert task.completion_note == '交付物已上传'

        forbidden_done = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'done'},
            format='json',
        )
        assert forbidden_done.status_code == 400
        task.refresh_from_db()
        assert task.status == 'pending_review'

    def test_creator_without_task_role_cannot_change_status(
        self, api_client, make_project, make_task, make_user,
    ):
        creator = make_user(email='task-creator-only@test.com')
        task = make_task(project=make_project(), creator=creator)
        api_client.force_authenticate(user=creator)

        response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'doing'},
            format='json',
        )

        assert response.status_code == 403

    def test_reviewer_only_handles_pending_review(
        self, api_client, make_project, make_task, make_user,
    ):
        reviewer = make_user(email='task-reviewer@test.com')
        task = make_task(project=make_project(), reviewer=reviewer)
        api_client.force_authenticate(user=reviewer)

        premature = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'doing'},
            format='json',
        )
        assert premature.status_code == 400

        task.status = 'pending_review'
        task.save(update_fields=['status'])
        completed = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'done'},
            format='json',
        )
        assert completed.status_code == 200, completed.json()
        task.refresh_from_db()
        assert task.status == 'done'
        assert task.completed_at is not None

    def test_project_leader_can_change_status_and_outsider_cannot(
        self, api_client, make_project, make_task, make_user,
    ):
        project = make_project()
        task = make_task(project=project)
        outsider = make_user(email='task-status-outsider@test.com')

        api_client.force_authenticate(user=project.leader)
        leader_response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'doing'},
            format='json',
        )
        assert leader_response.status_code == 200, leader_response.json()

        api_client.force_authenticate(user=outsider)
        outsider_response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'done'},
            format='json',
        )
        assert outsider_response.status_code == 403

    @pytest.mark.parametrize('role', ['teacher', 'sys_admin'])
    def test_teacher_and_admin_can_confirm_pending_review(
        self, role, api_client, make_project, make_task, make_user,
    ):
        operator = make_user(
            email=f'task-{role}@test.com',
            global_role=role,
        )
        task = make_task(project=make_project(), status='pending_review')
        api_client.force_authenticate(user=operator)

        response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'done'},
            format='json',
        )

        assert response.status_code == 200, response.json()

    def test_project_leader_cannot_skip_pending_review(
        self, api_client, make_project, make_task,
    ):
        project = make_project()
        task = make_task(project=project, status='doing')
        api_client.force_authenticate(user=project.leader)

        response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'done'},
            format='json',
        )

        assert response.status_code == 400
        assert '先提交待审核' in response.json()['message']
        task.refresh_from_db()
        assert task.status == 'doing'
        assert task.completed_at is None

    def test_overdue_requires_reason_for_action_and_regular_update(
        self, api_client, make_project, make_task,
    ):
        project = make_project()
        task = make_task(project=project, status='doing')
        api_client.force_authenticate(user=project.leader)

        action_response = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'overdue'},
            format='json',
        )
        assert action_response.status_code == 400

        update_response = api_client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'status': 'overdue'},
            format='json',
        )
        assert update_response.status_code == 400

        accepted = api_client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'status': 'overdue', 'delay_reason': '供应商材料晚到'},
            format='json',
        )
        assert accepted.status_code == 200, accepted.json()
        task.refresh_from_db()
        assert task.status == 'overdue'
        assert task.delay_reason == '供应商材料晚到'

    def test_regular_update_uses_same_transition_rules_and_keeps_notes(
        self, api_client, make_project, make_task, make_user,
    ):
        project = make_project()
        collaborator = make_user(email='task-form-collaborator@test.com')
        reviewer = make_user(email='task-form-reviewer@test.com')
        task = make_task(
            project=project,
            status='doing',
            reviewer=reviewer,
            delay_reason='原延期原因',
            completion_note='原完成说明',
        )
        task.collaborators.add(collaborator)
        api_client.force_authenticate(user=project.leader)

        skipped = api_client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'status': 'done', 'title': '不能部分保存的标题'},
            format='json',
        )
        assert skipped.status_code == 400
        task.refresh_from_db()
        assert task.status == 'doing'
        assert task.title != '不能部分保存的标题'

        updated = api_client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'title': '保留闭环字段的标题'},
            format='json',
        )
        assert updated.status_code == 200, updated.json()
        data = updated.json()['data']
        assert data['collaborator_ids'] == [collaborator.id]
        assert data['reviewer'] == reviewer.id
        assert data['delay_reason'] == '原延期原因'
        assert data['completion_note'] == '原完成说明'

        submitted = api_client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'status': 'pending_review', 'completion_note': '最终交付已完成'},
            format='json',
        )
        assert submitted.status_code == 200, submitted.json()
        task.refresh_from_db()
        assert task.status == 'pending_review'
        assert task.completion_note == '最终交付已完成'
        assert task.status_logs.filter(
            from_status='doing',
            to_status='pending_review',
            operator=project.leader,
        ).exists()

    def test_pause_and_cancel_are_reserved_for_task_managers(
        self, api_client, make_project, make_task, make_user,
    ):
        executor = make_user(email='task-pause-executor@test.com')
        project = make_project()
        task = make_task(project=project, assignee=executor, status='doing')

        api_client.force_authenticate(user=executor)
        forbidden = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'paused'},
            format='json',
        )
        assert forbidden.status_code == 400

        api_client.force_authenticate(user=project.leader)
        paused = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'paused'},
            format='json',
        )
        assert paused.status_code == 200, paused.json()

        cancelled = api_client.post(
            f'/api/v1/tasks/{task.id}/change_status/',
            {'to_status': 'cancelled'},
            format='json',
        )
        assert cancelled.status_code == 200, cancelled.json()

    def test_new_task_cannot_be_created_as_completed(
        self, api_client, make_project,
    ):
        project = make_project()
        api_client.force_authenticate(user=project.leader)

        response = api_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '试图跳过流程的任务',
            'assignee': project.leader_id,
            'status': 'done',
        }, format='json')

        assert response.status_code == 400

