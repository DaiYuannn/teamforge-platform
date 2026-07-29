import pytest
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.team_models import Team, TeamMember
from apps.users.models import User
from apps.users.serializers import UserCreateSerializer, UserUpdateSerializer


@pytest.mark.django_db
def test_only_one_active_operating_teacher_can_be_configured(make_user):
    operating_teacher = make_user(
        email='operating-teacher@test.com',
        global_role=User.GlobalRole.TEACHER,
        name='操作老师',
    )
    second_payload = {
        'username': 'second-teacher',
        'email': 'second-teacher@test.com',
        'name': '第二位老师',
        'global_role': User.GlobalRole.TEACHER,
        'is_student': False,
        'password': 'StrongPass123!',
        'password_confirm': 'StrongPass123!',
    }
    serializer = UserCreateSerializer(data=second_payload)

    assert not serializer.is_valid()
    assert 'global_role' in serializer.errors
    assert '只能设置一位' in str(serializer.errors['global_role'][0])

    demote = UserUpdateSerializer(
        operating_teacher,
        data={'global_role': User.GlobalRole.MEMBER},
        partial=True,
    )
    assert demote.is_valid(), demote.errors
    demote.save()

    retry = UserCreateSerializer(data=second_payload)
    assert retry.is_valid(), retry.errors


@pytest.mark.django_db
def test_database_rejects_a_second_active_operating_teacher(make_user):
    make_user(
        email='database-operating-teacher@test.com',
        global_role=User.GlobalRole.TEACHER,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        make_user(
            email='database-second-operating-teacher@test.com',
            global_role=User.GlobalRole.TEACHER,
        )

    exited_teacher = make_user(
        email='database-exited-teacher@test.com',
        global_role=User.GlobalRole.TEACHER,
        membership_status=User.MembershipStatus.EXITED,
    )
    assert exited_teacher.global_role == User.GlobalRole.TEACHER


@pytest.mark.django_db
def test_team_viewing_teacher_can_read_but_cannot_manage_team(
    api_client,
    make_user,
):
    owner = make_user(email='teacher-model-owner@test.com')
    viewing_teacher = make_user(
        email='viewing-teacher@test.com',
        global_role=User.GlobalRole.MEMBER,
        is_student=False,
    )
    team = Team.objects.create(name='只读老师所在团队', owner=owner)
    TeamMember.objects.create(
        team=team,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    TeamMember.objects.create(
        team=team,
        user=viewing_teacher,
        role=TeamMember.Role.TEACHER,
    )
    access = RefreshToken.for_user(viewing_teacher).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    detail_response = api_client.get(f'/api/v1/teams/{team.id}/')
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    detail = detail_payload.get('data', detail_payload)
    assert detail['can_manage'] is False

    update_response = api_client.patch(
        f'/api/v1/teams/{team.id}/',
        {'description': '不应被只读老师修改'},
        format='json',
    )
    assert update_response.status_code == 403
    team.refresh_from_db()
    assert team.description == ''
