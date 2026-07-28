from pathlib import Path

import openpyxl
import pytest
from django.core.exceptions import ValidationError

from apps.common.team_models import Team, TeamMember
from apps.imports.models import ImportTask
from apps.imports.services import ImportService
from apps.sensitive.models import SensitiveAccessRequest, SensitiveData
from apps.users.models import User


def extract_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


@pytest.mark.django_db
class TestSmallTeamHierarchyAndMembers:
    def test_hierarchy_is_limited_to_two_levels_and_co_lead_can_manage(
        self, api_client, make_user
    ):
        owner = make_user(email='org-owner@test.com')
        co_lead = make_user(email='co-lead@test.com')
        candidate = make_user(email='candidate@test.com', school='测试大学')
        root = Team.objects.create(name='总团队', code='ORG', owner=owner)
        TeamMember.objects.create(team=root, user=owner, role=TeamMember.Role.OWNER)
        child = Team.objects.create(
            name='小团队',
            code='SQUAD',
            owner=owner,
            parent=root,
            team_type=Team.TeamType.SQUAD,
        )
        TeamMember.objects.create(
            team=child,
            user=co_lead,
            role=TeamMember.Role.CO_LEAD,
        )

        with pytest.raises(ValidationError):
            Team.objects.create(
                name='非法第三级',
                owner=owner,
                parent=child,
                team_type=Team.TeamType.SQUAD,
            )

        api_client.force_authenticate(user=co_lead)
        response = api_client.post(
            f'/api/v1/teams/{child.id}/members/',
            {'user': candidate.id, 'role': TeamMember.Role.MEMBER},
            format='json',
        )
        assert response.status_code == 201, response.json()

        member_response = api_client.get(f'/api/v1/members/?team={child.id}')
        assert member_response.status_code == 200
        rows = extract_data(member_response)['results']
        row = next(item for item in rows if item['id'] == candidate.id)
        assert row['school'] == '测试大学'
        assert row['team_memberships'] == [
            {
                'team_id': child.id,
                'team_name': child.name,
                'parent_id': root.id,
                'parent_name': root.name,
                'role': TeamMember.Role.MEMBER,
                'role_display': '团队成员',
                'status': TeamMember.Status.ACTIVE,
            }
        ]


@pytest.mark.django_db
class TestSmallTeamSensitiveScope:
    def test_id_card_is_private_to_subject_and_team_reviewers(
        self, api_client, make_user
    ):
        owner_a = make_user(email='owner-a@test.com')
        co_lead_a = make_user(email='co-a@test.com')
        subject_a = make_user(email='subject-a@test.com')
        ordinary_a = make_user(email='ordinary-a@test.com')
        owner_b = make_user(email='owner-b@test.com')
        teacher = make_user(email='plain-teacher@test.com', global_role='teacher')
        team_a = Team.objects.create(name='A组', code='A-SCOPE', owner=owner_a)
        team_b = Team.objects.create(name='B组', code='B-SCOPE', owner=owner_b)
        for team, user, role in (
            (team_a, owner_a, TeamMember.Role.OWNER),
            (team_a, co_lead_a, TeamMember.Role.CO_LEAD),
            (team_a, subject_a, TeamMember.Role.MEMBER),
            (team_a, ordinary_a, TeamMember.Role.MEMBER),
            (team_b, owner_b, TeamMember.Role.OWNER),
        ):
            TeamMember.objects.create(team=team, user=user, role=role)
        identity = SensitiveData.objects.create(
            title='成员身份证',
            data_type=SensitiveData.DataType.ID_CARD,
            team=team_a,
            subject_user=subject_a,
            uploader=owner_a,
        )
        identity.encrypt_content('110101200001011234')

        for user, visible in (
            (subject_a, True),
            (co_lead_a, True),
            (ordinary_a, False),
            (owner_b, False),
        ):
            api_client.force_authenticate(user=user)
            rows = extract_data(api_client.get('/api/v1/sensitive/data/'))['results']
            assert (identity.id in {row['id'] for row in rows}) is visible

        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=identity,
            applicant=subject_a,
            reason='比赛报名提交证件',
        )
        api_client.force_authenticate(user=co_lead_a)
        approved = api_client.post(
            f'/api/v1/sensitive/requests/{request_obj.id}/approve/',
            {'action': 'approve', 'expire_hours': 1},
            format='json',
        )
        assert approved.status_code == 200, approved.json()

        api_client.force_authenticate(user=teacher)
        assert api_client.get(
            '/api/v1/sensitive/requests/pending_approve/'
        ).status_code == 403


@pytest.mark.django_db
class TestSmallTeamMemberImport:
    def test_member_import_sets_school_and_team_membership(
        self, tmp_path: Path, make_user
    ):
        owner = make_user(email='import-owner@test.com')
        team = Team.objects.create(name='导入小组', code='IMPORT-SQUAD', owner=owner)
        TeamMember.objects.create(team=team, user=owner, role=TeamMember.Role.OWNER)
        path = tmp_path / 'members.xlsx'
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(['姓名', '邮箱', '学校', '加入小团队编号'])
        sheet.append(['新成员', 'imported-member@test.com', '测试大学', team.code])
        workbook.save(path)
        headers, _rows = ImportService.parse_excel(str(path))
        task = ImportTask.objects.create(
            module=ImportTask.Module.MEMBERS,
            file_path=str(path),
            field_mapping=ImportService.auto_map_fields(headers, 'members'),
            created_by=owner,
            team=team,
            status=ImportTask.Status.PREVIEWED,
        )

        success, result = ImportService.confirm_import(task)

        assert success, result
        member = User.objects.get(email='imported-member@test.com')
        assert member.school == '测试大学'
        assert TeamMember.objects.filter(
            team=team,
            user=member,
            status=TeamMember.Status.ACTIVE,
        ).exists()
