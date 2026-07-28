"""
M07/N29: 全局搜索视图
跨模块搜索: 项目、任务、成员、文件、比赛、知识库文章、讨论主题
支持 search_type 参数限定搜索模块
"""
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from common.response import error_response, success_response
from common.schema import success_response_schema
from common.project_access import scope_project_queryset
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.users.models import User
from apps.files.models import FileAsset
from apps.files.permissions import scope_file_queryset
from apps.competitions.models import Competition
from apps.projects.knowledge_models import KnowledgeArticle
from apps.projects.discussion_models import DiscussionTopic


# 支持的搜索模块映射
SEARCH_MODULES = {
    'projects': 'projects',
    'tasks': 'tasks',
    'members': 'members',
    'files': 'files',
    'competitions': 'competitions',
    'knowledge': 'knowledge',
    'discussions': 'discussions',
}


class ProjectSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    status = serializers.CharField()
    leader_name = serializers.CharField(allow_blank=True)
    url = serializers.CharField()


class TaskSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    priority = serializers.CharField()
    project_name = serializers.CharField(allow_blank=True)
    assignee_name = serializers.CharField(allow_blank=True)
    url = serializers.CharField()


class MemberSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    global_role = serializers.CharField()
    global_role_display = serializers.CharField()
    avatar = serializers.CharField(allow_blank=True)
    url = serializers.CharField()


class FileSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    level = serializers.CharField()
    level_display = serializers.CharField()
    project_name = serializers.CharField(allow_blank=True)
    uploader_name = serializers.CharField(allow_blank=True)
    url = serializers.CharField()


class CompetitionSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    url = serializers.CharField()


class KnowledgeSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    category = serializers.CharField()
    category_display = serializers.CharField()
    author_name = serializers.CharField(allow_blank=True)
    project_name = serializers.CharField(allow_blank=True)
    tags = serializers.CharField(allow_blank=True)
    url = serializers.CharField()


class DiscussionSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    project_name = serializers.CharField(allow_blank=True)
    author_name = serializers.CharField(allow_blank=True)
    is_pinned = serializers.BooleanField()
    is_closed = serializers.BooleanField()
    reply_count = serializers.IntegerField()
    url = serializers.CharField()


class GlobalSearchDataSerializer(serializers.Serializer):
    projects = ProjectSearchResultSerializer(many=True)
    tasks = TaskSearchResultSerializer(many=True)
    members = MemberSearchResultSerializer(many=True)
    files = FileSearchResultSerializer(many=True)
    competitions = CompetitionSearchResultSerializer(many=True)
    knowledge = KnowledgeSearchResultSerializer(many=True)
    discussions = DiscussionSearchResultSerializer(many=True)
    total = serializers.IntegerField()
    query = serializers.CharField(allow_blank=True)
    search_type = serializers.CharField(allow_null=True)


class GlobalSearchView(APIView):
    """
    全局搜索
    GET /api/v1/dashboard/search/?q=关键词&limit=5&search_type=knowledge
    搜索范围: 项目、任务、成员、文件、比赛、知识库文章、讨论主题
    search_type 可选: projects/tasks/members/files/competitions/knowledge/discussions
    不传 search_type 时搜索全部模块
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='limit', type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, default=5,
                description='Maximum results per active module (capped at 20).',
            ),
            OpenApiParameter(
                name='search_type', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
                description=(
                    'Comma-separated subset of projects, tasks, members, files, '
                    'competitions, knowledge, and discussions.'
                ),
            ),
        ],
        responses={
            200: success_response_schema(
                'GlobalSearchResponse', GlobalSearchDataSerializer(),
            ),
        },
    )
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            limit = 0
        if not 1 <= limit <= 20:
            return error_response(
                message='limit must be an integer between 1 and 20.',
                code=1005,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        # search_type 限定搜索模块；多个模块用逗号分隔
        search_type_raw = request.query_params.get('search_type', '').strip()
        if search_type_raw:
            requested = {t.strip() for t in search_type_raw.split(',') if t.strip()}
            active_modules = {k: v for k, v in SEARCH_MODULES.items() if k in requested}
        else:
            active_modules = dict(SEARCH_MODULES)

        # 空结果骨架
        results = {
            'projects': [],
            'tasks': [],
            'members': [],
            'files': [],
            'competitions': [],
            'knowledge': [],
            'discussions': [],
        }

        if not query:
            return success_response({
                **results,
                'total': 0,
                'query': '',
                'search_type': search_type_raw or None,
            })

        # 搜索项目
        if 'projects' in active_modules:
            projects = scope_project_queryset(
                Project.objects.filter(
                    Q(name__icontains=query) |
                    Q(code__icontains=query) |
                    Q(intro__icontains=query)
                ),
                request.user,
                project_lookup='',
            ).filter(
                Q(status='active') | Q(status='archived')
            ).select_related('leader')[:limit]
            results['projects'] = [{
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'status': p.status,
                'leader_name': p.leader.name if p.leader else '',
                'url': f'/projects/{p.id}',
            } for p in projects]

        # 搜索任务
        if 'tasks' in active_modules:
            tasks = scope_project_queryset(Task.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            ), request.user).select_related('project', 'assignee')[:limit]
            results['tasks'] = [{
                'id': t.id,
                'title': t.title,
                'status': t.status,
                'status_display': t.get_status_display(),
                'priority': t.priority,
                'project_name': t.project.name if t.project else '',
                'assignee_name': t.assignee.name if t.assignee else '',
                'url': f'/tasks?task_id={t.id}',
            } for t in tasks]

        # 搜索成员
        if 'members' in active_modules:
            members = User.objects.filter(
                Q(name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            ).filter(is_active=True)[:limit]
            results['members'] = [{
                'id': m.id,
                'name': m.name,
                'email': m.email,
                'global_role': m.global_role,
                'global_role_display': m.get_global_role_display(),
                'avatar': m.avatar.url if m.avatar else '',
                'url': f'/members/{m.id}',
            } for m in members]

        # 搜索文件
        if 'files' in active_modules:
            files = scope_file_queryset(
                FileAsset.objects.filter(Q(name__icontains=query)),
                request.user,
            ).select_related('project', 'uploader')[:limit]
            results['files'] = [{
                'id': f.id,
                'name': f.name,
                'level': f.level,
                'level_display': f.get_level_display(),
                'project_name': f.project.name if f.project else '',
                'uploader_name': f.uploader.name if f.uploader else '',
                'url': f'/files?file_id={f.id}',
            } for f in files]

        # 搜索比赛
        if 'competitions' in active_modules:
            competitions = scope_project_queryset(Competition.objects.filter(
                Q(name__icontains=query) |
                Q(organizer__icontains=query) |
                Q(comp_type__icontains=query)
            ), request.user)[:limit]
            results['competitions'] = [{
                'id': c.id,
                'name': c.name,
                'status': c.status,
                'url': f'/competitions?competition_id={c.id}',
            } for c in competitions]

        # 搜索知识库文章
        if 'knowledge' in active_modules:
            articles = scope_project_queryset(KnowledgeArticle.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__icontains=query)
            ), request.user, include_unscoped=True).select_related(
                'author', 'project'
            )[:limit]
            results['knowledge'] = [{
                'id': a.id,
                'title': a.title,
                'category': a.category,
                'category_display': a.get_category_display(),
                'author_name': a.author.name if a.author else '',
                'project_name': a.project.name if a.project else '',
                'tags': a.tags,
                'url': (
                    f'/projects/{a.project_id}/operations?tab=knowledge'
                    f'&article_id={a.id}'
                ) if a.project_id else '/projects',
            } for a in articles]

        # 搜索讨论主题
        if 'discussions' in active_modules:
            topics = scope_project_queryset(DiscussionTopic.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query)
            ), request.user).select_related('project', 'author')[:limit]
            results['discussions'] = [{
                'id': t.id,
                'title': t.title,
                'project_name': t.project.name if t.project else '',
                'author_name': t.author.name if t.author else '',
                'is_pinned': t.is_pinned,
                'is_closed': t.is_closed,
                'reply_count': t.reply_count,
                'url': (
                    f'/projects/{t.project_id}/operations?tab=discussions'
                    f'&discussion_id={t.id}'
                ),
            } for t in topics]

        # 总结果数（只计算活跃模块）
        total = sum(len(results[k]) for k in active_modules)

        return success_response({
            **results,
            'total': total,
            'query': query,
            'search_type': search_type_raw or None,
        })
