"""
项目模板视图
- ProjectTemplateViewSet: 模板 CRUD + instantiate（从模板创建项目）
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from common.project_access import is_external_collaborator
from .template_models import ProjectTemplate
from .template_serializers import (
    ProjectTemplateSerializer,
    ProjectTemplateInstantiateSerializer,
)


class ProjectTemplateViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    项目模板管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 老师/管理员
    - instantiate: 从模板实例化项目
    """
    queryset = ProjectTemplate.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': ProjectTemplateSerializer,
        'retrieve': ProjectTemplateSerializer,
        'create': ProjectTemplateSerializer,
        'update': ProjectTemplateSerializer,
        'partial_update': ProjectTemplateSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsTeacherOrAdmin],
        'update': [IsTeacherOrAdmin],
        'partial_update': [IsTeacherOrAdmin],
        'destroy': [IsTeacherOrAdmin],
        'instantiate': [IsTeacherOrAdmin],
    }

    filterset_fields = ['category', 'is_active', 'created_by']
    search_fields = ['name', 'description', 'category']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_external_collaborator(self.request.user):
            return queryset.none()
        return queryset

    def create(self, request, *args, **kwargs):
        """创建模板，自动设置创建人为当前用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.save(created_by=request.user)
        return success_response(
            ProjectTemplateSerializer(template).data,
            message='模板创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新模板"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return success_response(ProjectTemplateSerializer(template).data, message='模板更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除模板"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='模板已删除')

    @action(detail=True, methods=['post'])
    def instantiate(self, request, pk=None):
        """
        从模板实例化（创建）项目
        POST /api/v1/projects/templates/{id}/instantiate/
        body: {
            "name": "项目名称",
            "code": "PROJ-0001",
            "leader": 1,
            "intro": "项目简介",
            "start_date": "2026-01-01",
            "planned_end_date": "2026-12-31"
        }
        根据 config 中的 milestones / tasks 自动创建里程碑与任务
        """
        template = self.get_object()
        if not template.is_active:
            return error_response(message='该模板已停用，无法实例化')

        # 校验请求参数
        input_serializer = ProjectTemplateInstantiateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        # 创建项目（复用 ProjectCreateSerializer 的逻辑）
        from .serializers import ProjectCreateSerializer
        from apps.users.models import User
        from .milestone_models import Milestone
        from apps.tasks.models import Task, TaskLog

        try:
            leader = User.objects.get(id=data['leader'])
        except User.DoesNotExist:
            return error_response(message='指定的项目负责人不存在')

        project_data = {
            'name': data['name'],
            'code': data['code'],
            'leader': leader.id,
            'intro': data.get('intro', ''),
            'priority': data.get('priority', 'normal'),
        }
        if data.get('start_date'):
            project_data['start_date'] = data['start_date'].isoformat()
        if data.get('planned_end_date'):
            project_data['planned_end_date'] = data['planned_end_date'].isoformat()

        create_serializer = ProjectCreateSerializer(
            data=project_data,
            context={'request': request},
        )
        create_serializer.is_valid(raise_exception=True)
        project = create_serializer.save()

        config = template.config or {}

        # 根据模板配置创建里程碑
        created_milestones = 0
        for ms in config.get('milestones', []) or []:
            Milestone.objects.create(
                project=project,
                title=ms.get('title', '里程碑'),
                description=ms.get('description', ''),
                due_date=ms.get('due_date') or None,
                sort_order=ms.get('sort_order', 0),
            )
            created_milestones += 1

        # 根据模板配置创建任务
        created_tasks = 0
        for tk in config.get('tasks', []) or []:
            task = Task.objects.create(
                project=project,
                title=tk.get('title', '任务'),
                description=tk.get('description', ''),
                assignee=leader,
                creator=request.user,
                priority=tk.get('priority', 'medium'),
            )
            TaskLog.objects.create(
                task=task,
                from_status='',
                to_status=task.status,
                operator=request.user,
            )
            created_tasks += 1

        from .serializers import ProjectSerializer
        result = ProjectSerializer(
            project,
            context={'request': request},
        ).data
        result['_instantiated'] = {
            'milestones': created_milestones,
            'tasks': created_tasks,
        }
        return success_response(
            result,
            message=f'项目已从模板创建，含 {created_milestones} 个里程碑、{created_tasks} 个任务',
            http_status=status.HTTP_201_CREATED,
        )
