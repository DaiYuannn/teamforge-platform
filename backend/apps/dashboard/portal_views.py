"""公开门户设置、逐项发布和成员授权接口。"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.permissions import IsTeacherOrAdmin
from common.response import error_response, success_response

from .portal_models import PortalPublication, PortalSettings
from .portal_serializers import (
    PortalMemberConsentSerializer,
    PortalPublicationSerializer,
    PortalSettingsSerializer,
)


def get_portal_settings():
    settings, _ = PortalSettings.objects.get_or_create(singleton_key='default')
    return settings


def _publication_payload(content_type, object_id, publication_map):
    publication = publication_map.get((content_type, object_id))
    return {
        'content_type': content_type,
        'object_id': object_id,
        'is_public': publication.is_public if publication else False,
        'is_featured': publication.is_featured if publication else False,
        'member_consent': publication.member_consent if publication else False,
        'display_order': publication.display_order if publication else 0,
        'custom_title': publication.custom_title if publication else '',
        'custom_summary': publication.custom_summary if publication else '',
        'image_url': publication.image_url if publication else '',
    }


class PortalManagementView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        from apps.intellectual_property.models import IntellectualPropertyApplication
        from apps.projects.models import Project
        from apps.users.models import User

        publication_map = {
            (item.content_type, item.object_id): item
            for item in PortalPublication.objects.all()
        }
        projects = []
        for project in Project.objects.select_related('leader').order_by('-updated_at'):
            item = _publication_payload(
                PortalPublication.ContentType.PROJECT, project.id, publication_map
            )
            item.update({
                'name': project.name,
                'code': project.code,
                'secondary': project.leader.name if project.leader else '',
                'status': project.status,
            })
            projects.append(item)

        ip_applications = []
        for application in IntellectualPropertyApplication.objects.order_by('-updated_at'):
            item = _publication_payload(
                PortalPublication.ContentType.IP_APPLICATION,
                application.id,
                publication_map,
            )
            item.update({
                'name': application.title,
                'code': application.application_code,
                'secondary': application.get_ip_type_display(),
                'status': application.status,
            })
            ip_applications.append(item)

        members = []
        for member in User.objects.filter(is_active=True).order_by('name'):
            item = _publication_payload(
                PortalPublication.ContentType.MEMBER, member.id, publication_map
            )
            item.update({
                'name': member.name,
                'code': member.email,
                'secondary': member.get_global_role_display(),
                'status': getattr(member, 'membership_status', 'active'),
            })
            members.append(item)

        return success_response({
            'settings': PortalSettingsSerializer(get_portal_settings()).data,
            'projects': projects,
            'ip_applications': ip_applications,
            'members': members,
        })

    def patch(self, request):
        instance = get_portal_settings()
        serializer = PortalSettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return success_response(serializer.data, message='门户资料已更新')


class PortalPublicationView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    @staticmethod
    def _object_exists(content_type, object_id):
        if content_type == PortalPublication.ContentType.PROJECT:
            from apps.projects.models import Project
            return Project.objects.filter(pk=object_id).exists()
        if content_type == PortalPublication.ContentType.IP_APPLICATION:
            from apps.intellectual_property.models import IntellectualPropertyApplication
            return IntellectualPropertyApplication.objects.filter(pk=object_id).exists()
        if content_type == PortalPublication.ContentType.MEMBER:
            from apps.users.models import User
            return User.objects.filter(pk=object_id).exists()
        return False

    def patch(self, request, content_type, object_id):
        valid_types = {choice[0] for choice in PortalPublication.ContentType.choices}
        if content_type not in valid_types or not self._object_exists(content_type, object_id):
            return error_response(message='公开对象不存在', code=1004)

        publication, _ = PortalPublication.objects.get_or_create(
            content_type=content_type,
            object_id=object_id,
        )
        serializer = PortalPublicationSerializer(
            publication, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return success_response(serializer.data, message='公开设置已更新')


class PortalMemberConsentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        publication = PortalPublication.objects.filter(
            content_type=PortalPublication.ContentType.MEMBER,
            object_id=request.user.id,
        ).first()
        return success_response({
            'consent': publication.member_consent if publication else False,
            'is_public': publication.is_public if publication else False,
        })

    def patch(self, request):
        serializer = PortalMemberConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = serializer.validated_data['consent']
        publication, _ = PortalPublication.objects.get_or_create(
            content_type=PortalPublication.ContentType.MEMBER,
            object_id=request.user.id,
        )
        publication.member_consent = consent
        if not consent:
            publication.is_public = False
        publication.updated_by = request.user
        publication.save(update_fields=[
            'member_consent', 'is_public', 'updated_by', 'updated_at',
        ])
        return success_response({
            'consent': publication.member_consent,
            'is_public': publication.is_public,
        }, message='公开授权已更新')
