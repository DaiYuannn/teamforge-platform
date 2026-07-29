"""
动态流视图
- ActivityFeedView: 全局动态流（分页，可按 project / type / actor 过滤）
- ProjectActivityView: 指定项目的动态流（分页，可按 type / actor 过滤）

接口：
- GET /api/v1/activities/?project=&type=&actor=&page=&page_size=
- GET /api/v1/activities/project/<project_id>/?type=&actor=&page=&page_size=
"""
from django.db.models import Q
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from common.project_access import (
    active_user_root_team_ids,
    scope_project_queryset,
)
from .activity_models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    """动态流序列化器"""
    type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    actor_name = serializers.CharField(source='actor.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    project_code = serializers.CharField(source='project.code', read_only=True, default='')
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True,
        default='',
    )

    class Meta:
        model = Activity
        fields = (
            'id', 'activity_type', 'type_display',
            'actor', 'actor_name',
            'project', 'project_name', 'project_code',
            'organization', 'organization_name',
            'target_type', 'target_id', 'description', 'metadata',
            'created_at',
        )
        read_only_fields = fields


class ActivityFeedView(GenericAPIView):
    """
    全局动态流
    GET /api/v1/activities/
    查询参数：
      - project: 按项目ID过滤
      - type:    按动态类型过滤
      - actor:   按操作人ID过滤
      - page / page_size: 分页
    """
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    queryset = Activity.objects.none()

    def get_queryset(self):
        queryset = Activity.objects.select_related(
            'actor',
            'project',
            'organization',
        ).all()
        user = self.request.user
        if user.global_role not in ('sys_admin', 'teacher'):
            from apps.common.team_models import Team
            from apps.projects.models import Project

            if Team.objects.filter(
                parent__isnull=True,
                is_active=True,
            ).exists():
                project_ids = scope_project_queryset(
                    Project.objects.all(),
                    user,
                ).values('id')
                root_ids = active_user_root_team_ids(user)
                queryset = queryset.filter(
                    Q(project_id__in=project_ids)
                    | Q(organization_id__in=root_ids)
                    | Q(
                        actor=user,
                        project__isnull=True,
                        organization__isnull=True,
                    )
                ).distinct()
        project = self.request.query_params.get('project')
        activity_type = self.request.query_params.get('type')
        actor = self.request.query_params.get('actor')
        if project:
            queryset = queryset.filter(project_id=project)
        if activity_type:
            type_groups = {
                'competition': [
                    Activity.Type.COMPETITION_CREATED,
                    Activity.Type.COMPETITION_UPDATED,
                    Activity.Type.COMPETITION_AWARDED,
                ],
                'finance': [
                    Activity.Type.FINANCE_EXPENSE,
                    Activity.Type.FINANCE_PAYMENT,
                    Activity.Type.FINANCE_INCOME,
                ],
                'intellectual_property': [
                    Activity.Type.IP_CREATED,
                    Activity.Type.IP_UPDATED,
                    Activity.Type.IP_AUTHORIZED,
                ],
            }
            if activity_type in type_groups:
                queryset = queryset.filter(
                    activity_type__in=type_groups[activity_type]
                )
            else:
                queryset = queryset.filter(activity_type=activity_type)
        if actor:
            queryset = queryset.filter(actor_id=actor)
        return queryset

    def get(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)


class ProjectActivityView(GenericAPIView):
    """
    项目动态流
    GET /api/v1/activities/project/<project_id>/
    查询参数：
      - type:  按动态类型过滤
      - actor: 按操作人ID过滤
      - page / page_size: 分页
    """
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    queryset = Activity.objects.none()

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        queryset = Activity.objects.filter(
            project_id=project_id
        ).select_related('actor', 'project')
        activity_type = self.request.query_params.get('type')
        actor = self.request.query_params.get('actor')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        if actor:
            queryset = queryset.filter(actor_id=actor)
        return queryset

    def get(self, request, project_id):
        from apps.common.team_models import Team
        from apps.projects.models import Project
        project = Project.objects.filter(id=project_id).first()
        if project is None:
            return error_response(message='项目不存在', code=1004, http_status=404)
        if (
            request.user.global_role not in ('sys_admin', 'teacher')
            and Team.objects.filter(
                parent__isnull=True,
                is_active=True,
            ).exists()
            and not scope_project_queryset(
                Project.objects.all(),
                request.user,
            ).filter(id=project_id).exists()
        ):
            return error_response(
                message='无权查看该项目动态',
                code=1003,
                http_status=403,
            )

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
