"""
N40: 多团队支持测试
- /api/v1/teams/                团队 CRUD + 成员管理
- /api/v1/team-members/         团队成员 CRUD
"""
import pytest

from apps.common.team_models import Team, TeamMember, TeamMembershipEvent


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def extract_rows(response):
    data = extract_data(response)
    if isinstance(data, dict):
        return data.get('results', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestTeam:
    """多团队测试"""

    def test_create_team(self, member_client):
        """创建团队，创建人自动成为 owner 成员"""
        resp = member_client.post('/api/v1/teams/', {
            'name': '测试团队', 'description': '描述',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        team_id = data['id']
        team = Team.objects.get(id=team_id)
        assert team.owner == member_client.user
        # 创建人自动加入为 owner
        assert TeamMember.objects.filter(team=team, user=member_client.user, role='owner').exists()

    def test_list_teams_only_mine(self, member_client, make_user, api_client):
        """仅能看到自己拥有或加入的团队"""
        other = make_user(email='other-team@test.com')
        Team.objects.create(name='他人团队', owner=other)
        resp = member_client.get('/api/v1/teams/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        names = [t['name'] for t in items]
        assert '他人团队' not in names

    def test_retrieve_team(self, member_client):
        """查看团队详情"""
        team = Team.objects.create(name='详情团队', owner=member_client.user)
        resp = member_client.get(f'/api/v1/teams/{team.id}/')
        assert resp.status_code == 200
        assert extract_data(resp)['name'] == '详情团队'

    def test_update_team(self, member_client):
        """更新团队"""
        team = Team.objects.create(name='待更新', owner=member_client.user)
        resp = member_client.patch(f'/api/v1/teams/{team.id}/', {
            'description': '新描述',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        team.refresh_from_db()
        assert team.description == '新描述'

    def test_delete_team(self, member_client):
        """删除团队"""
        team = Team.objects.create(name='待删除', owner=member_client.user)
        resp = member_client.delete(f'/api/v1/teams/{team.id}/')
        assert resp.status_code in (200, 204)
        assert not Team.objects.filter(id=team.id).exists()

    def test_add_member(self, member_client, make_user):
        """添加团队成员"""
        team = Team.objects.create(name='成员团队', owner=member_client.user)
        new_user = make_user(email='newmember@test.com')
        resp = member_client.post(f'/api/v1/teams/{team.id}/members/', {
            'user': new_user.id, 'role': 'member',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        assert TeamMember.objects.filter(team=team, user=new_user, role='member').exists()

    def test_add_duplicate_member(self, member_client, make_user):
        """重复添加成员"""
        team = Team.objects.create(name='重复成员团队', owner=member_client.user)
        new_user = make_user(email='dup@test.com')
        member_client.post(f'/api/v1/teams/{team.id}/members/', {
            'user': new_user.id,
        }, format='json')
        resp = member_client.post(f'/api/v1/teams/{team.id}/members/', {
            'user': new_user.id,
        }, format='json')
        assert resp.status_code in (400, 409)

    def test_list_members(self, member_client, make_user):
        """列出团队成员"""
        team = Team.objects.create(name='列表团队', owner=member_client.user)
        u = make_user(email='lm@test.com')
        TeamMember.objects.create(team=team, user=u, role='member')
        resp = member_client.get(f'/api/v1/teams/{team.id}/members/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert any(m['user'] == u.id for m in data)

    def test_member_lists_use_same_role_priority_order_for_child_team(
        self, member_client, make_user
    ):
        """老师最前、负责人角色居中、普通成员按姓名稳定排序。"""
        root = Team.objects.create(
            name='排序总团队',
            owner=member_client.user,
        )
        child_owner = make_user(
            email='ordered-owner@test.com',
            name='小组主负责人',
        )
        child = Team.objects.create(
            name='排序小团队',
            owner=child_owner,
            parent=root,
            team_type=Team.TeamType.SQUAD,
        )
        member_specs = (
            ('teacher', 'ordered-teacher@test.com', '指导教师'),
            ('owner', 'ordered-owner@test.com', '小组主负责人'),
            ('co_lead', 'ordered-co-lead@test.com', '共同负责人'),
            ('admin', 'ordered-admin@test.com', '团队管理员'),
            ('advisor', 'ordered-advisor@test.com', '项目顾问'),
            ('member', 'ordered-member-b@test.com', 'B成员'),
            ('member', 'ordered-member-a@test.com', 'A成员'),
            ('external', 'ordered-external@test.com', '外部成员'),
        )
        expected_ids = []
        created_by_email = {child_owner.email: child_owner}
        for role, email, name in member_specs:
            user = created_by_email.get(email) or make_user(
                email=email,
                name=name,
            )
            membership = TeamMember.objects.create(
                team=child,
                user=user,
                role=role,
            )
            created_by_email[email] = user
            if role != TeamMember.Role.MEMBER:
                expected_ids.append(membership.user_id)
        member_ids = sorted(
            (
                membership.user.name,
                membership.user_id,
            )
            for membership in TeamMember.objects.filter(
                team=child,
                role=TeamMember.Role.MEMBER,
            ).select_related('user')
        )
        expected_ids[5:5] = [user_id for _, user_id in member_ids]

        nested = member_client.get(
            f'/api/v1/teams/{child.id}/members/'
        )
        standalone = member_client.get(
            '/api/v1/team-members/',
            {'team': child.id},
        )

        assert nested.status_code == 200
        assert standalone.status_code == 200
        assert [row['user'] for row in extract_rows(nested)] == expected_ids
        assert [row['user'] for row in extract_rows(standalone)] == expected_ids

    def test_member_lists_share_role_school_and_status_filters(
        self, member_client, make_user, api_client
    ):
        root = Team.objects.create(
            name='筛选总团队',
            owner=member_client.user,
        )
        child_owner = make_user(email='filter-child-owner@test.com')
        child = Team.objects.create(
            name='筛选小团队',
            owner=child_owner,
            parent=root,
            team_type=Team.TeamType.SQUAD,
        )
        teacher = make_user(
            email='filter-teacher@test.com',
            name='筛选教师',
            school='示范大学',
        )
        account_on_leave = make_user(
            email='filter-account-leave@test.com',
            name='账号暂离成员',
            school='示范大学',
            membership_status='on_leave',
        )
        team_on_leave = make_user(
            email='filter-team-leave@test.com',
            name='小组暂离管理员',
            school='其他大学',
        )
        external = make_user(
            email='filter-external@test.com',
            name='外部成员',
            school='示范大学',
            membership_status='external',
        )
        memberships = {
            'teacher': TeamMember.objects.create(
                team=child,
                user=teacher,
                role=TeamMember.Role.TEACHER,
            ),
            'account_on_leave': TeamMember.objects.create(
                team=child,
                user=account_on_leave,
                role=TeamMember.Role.MEMBER,
            ),
            'team_on_leave': TeamMember.objects.create(
                team=child,
                user=team_on_leave,
                role=TeamMember.Role.ADMIN,
                status=TeamMember.Status.ON_LEAVE,
            ),
            'external': TeamMember.objects.create(
                team=child,
                user=external,
                role=TeamMember.Role.EXTERNAL,
            ),
        }
        cases = (
            ({'role': TeamMember.Role.TEACHER}, {memberships['teacher'].id}),
            (
                {'school': '示范'},
                {
                    memberships['teacher'].id,
                    memberships['account_on_leave'].id,
                    memberships['external'].id,
                },
            ),
            (
                {'status': TeamMember.Status.ON_LEAVE},
                {memberships['team_on_leave'].id},
            ),
            (
                {'membership_status': 'on_leave'},
                {memberships['account_on_leave'].id},
            ),
        )
        for params, expected_ids in cases:
            nested = member_client.get(
                f'/api/v1/teams/{child.id}/members/',
                params,
            )
            standalone = member_client.get(
                '/api/v1/team-members/',
                {'team': child.id, **params},
            )
            assert nested.status_code == 200
            assert standalone.status_code == 200
            assert {
                row['id'] for row in extract_rows(nested)
            } == expected_ids
            assert {
                row['id'] for row in extract_rows(standalone)
            } == expected_ids

        outsider = make_user(email='member-filter-outsider@test.com')
        Team.objects.create(name='另一个总团队', owner=outsider)
        api_client.force_authenticate(user=outsider)
        assert api_client.get(
            f'/api/v1/teams/{child.id}/members/'
        ).status_code == 404
        isolated_rows = extract_rows(api_client.get(
            '/api/v1/team-members/',
            {'team': child.id},
        ))
        assert isolated_rows == []

    def test_active_root_teacher_can_view_child_but_cannot_manage(
        self, member_client, make_user, api_client
    ):
        root = Team.objects.create(
            name='Root team for teacher visibility',
            owner=member_client.user,
        )
        teacher = make_user(
            email='root-team-teacher@test.com',
            global_role='teacher',
        )
        TeamMember.objects.create(
            team=root,
            user=teacher,
            role=TeamMember.Role.TEACHER,
            status=TeamMember.Status.ACTIVE,
        )
        child_owner = make_user(email='teacher-visible-child-owner@test.com')
        child = Team.objects.create(
            name='Teacher visible child team',
            owner=child_owner,
            parent=root,
            team_type=Team.TeamType.SQUAD,
        )
        child_member = make_user(email='teacher-visible-child-member@test.com')
        child_membership = TeamMember.objects.create(
            team=child,
            user=child_member,
            role=TeamMember.Role.MEMBER,
        )
        candidate = make_user(email='teacher-forbidden-candidate@test.com')
        api_client.force_authenticate(user=teacher)

        team_list = api_client.get('/api/v1/teams/')
        child_members = api_client.get(
            f'/api/v1/teams/{child.id}/members/'
        )
        update = api_client.patch(
            f'/api/v1/teams/{child.id}/',
            {'description': 'Teacher must not be able to update this team.'},
            format='json',
        )
        add_member = api_client.post(
            f'/api/v1/teams/{child.id}/members/',
            {'user': candidate.id, 'role': TeamMember.Role.MEMBER},
            format='json',
        )

        assert team_list.status_code == 200
        assert {row['id'] for row in extract_rows(team_list)} >= {
            root.id,
            child.id,
        }
        assert child_members.status_code == 200
        assert child_membership.id in {
            row['id'] for row in extract_rows(child_members)
        }
        assert update.status_code == 403
        assert add_member.status_code == 403
        assert not TeamMember.objects.filter(
            team=child,
            user=candidate,
        ).exists()

    def test_invalid_role_and_status_filters_are_consistent(
        self, member_client
    ):
        team = Team.objects.create(
            name='Invalid member filter team',
            owner=member_client.user,
        )
        TeamMember.objects.create(
            team=team,
            user=member_client.user,
            role=TeamMember.Role.OWNER,
        )

        for params in (
            {'role': 'not-a-role'},
            {'status': 'not-a-status'},
        ):
            nested = member_client.get(
                f'/api/v1/teams/{team.id}/members/',
                params,
            )
            standalone = member_client.get(
                '/api/v1/team-members/',
                {'team': team.id, **params},
            )

            assert nested.status_code == 200
            assert standalone.status_code == 200
            assert extract_rows(nested) == []
            assert extract_rows(standalone) == []

    def test_remove_member(self, member_client, make_user):
        """成员离队保留关系和历史"""
        team = Team.objects.create(name='移除团队', owner=member_client.user)
        u = make_user(email='rm@test.com')
        m = TeamMember.objects.create(team=team, user=u, role='member')
        resp = member_client.delete(f'/api/v1/teams/{team.id}/members/{m.id}/')
        assert resp.status_code == 200
        m.refresh_from_db()
        assert m.status == TeamMember.Status.EXITED
        assert m.left_at is not None
        assert TeamMembershipEvent.objects.filter(
            membership=m, event_type='exited'
        ).exists()

    def test_member_count(self, member_client, make_user):
        """成员计数"""
        team = Team.objects.create(name='计数团队', owner=member_client.user)
        u1 = make_user(email='cnt1@test.com')
        u2 = make_user(email='cnt2@test.com')
        TeamMember.objects.create(team=team, user=u1, role='member')
        TeamMember.objects.create(team=team, user=u2, role='member')
        resp = member_client.get(f'/api/v1/teams/{team.id}/')
        assert extract_data(resp)['member_count'] >= 2

    def test_team_member_crud(self, member_client, make_user):
        """团队成员独立 CRUD"""
        team = Team.objects.create(name='CRUD团队', owner=member_client.user)
        u = make_user(email='crud@test.com')
        resp = member_client.post('/api/v1/team-members/', {
            'team': team.id, 'user': u.id, 'role': 'admin',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        assert TeamMember.objects.filter(team=team, user=u, role='admin').exists()

    def test_non_manager_cannot_add_team_member(
        self, member_client, make_user, api_client
    ):
        owner = make_user(email='team-owner@test.com')
        team = Team.objects.create(name='权限团队', owner=owner)
        TeamMember.objects.create(team=team, user=member_client.user, role='member')
        candidate = make_user(email='team-candidate@test.com')

        resp = member_client.post(
            f'/api/v1/teams/{team.id}/members/',
            {'user': candidate.id, 'role': 'member'},
            format='json',
        )

        assert resp.status_code == 403
        assert not TeamMember.objects.filter(team=team, user=candidate).exists()

    def test_transfer_owner_preserves_both_memberships(self, member_client, make_user):
        team = Team.objects.create(name='交接团队', owner=member_client.user)
        old_owner = TeamMember.objects.create(
            team=team, user=member_client.user, role=TeamMember.Role.OWNER
        )
        successor = make_user(email='team-successor@test.com')
        successor_membership = TeamMember.objects.create(
            team=team, user=successor, role=TeamMember.Role.MEMBER
        )

        resp = member_client.post(
            f'/api/v1/teams/{team.id}/transfer-owner/',
            {'member_id': successor_membership.id, 'reason': '届满交接'},
            format='json',
        )

        assert resp.status_code == 200, resp.json()
        team.refresh_from_db()
        old_owner.refresh_from_db()
        successor_membership.refresh_from_db()
        assert team.owner_id == successor.id
        assert old_owner.role == TeamMember.Role.CO_LEAD
        assert successor_membership.role == TeamMember.Role.OWNER
        assert TeamMembershipEvent.objects.filter(
            membership=successor_membership,
            event_type='role_changed',
        ).exists()

    def test_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.get('/api/v1/teams/')
        assert resp.status_code in (401, 403)
