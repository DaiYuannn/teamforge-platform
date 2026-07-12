"""
M07/N29: 全局搜索视图
跨模块搜索: 项目、任务、成员、文件、比赛、知识库文章、讨论主题
支持 search_type 参数限定搜索模块
"""
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.users.models import User
from apps.files.models import FileAsset
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


class GlobalSearchView(APIView):
    """
    全局搜索
    GET /api/v1/dashboard/search/?q=关键词&limit=5&search_type=knowledge
    搜索范围: 项目、任务、成员、文件、比赛、知识库文章、讨论主题
    search_type 可选: projects/tasks/members/files/competitions/knowledge/discussions
    不传 search_type 时搜索全部模块
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        limit = min(int(request.query_params.get('limit', 5)), 20)
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
            projects = Project.objects.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(intro__icontains=query)
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
            tasks = Task.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            ).select_related('project', 'assignee')[:limit]
            results['tasks'] = [{
                'id': t.id,
                'title': t.title,
                'status': t.status,
                'status_display': t.get_status_display(),
                'priority': t.priority,
                'project_name': t.project.name if t.project else '',
                'assignee_name': t.assignee.name if t.assignee else '',
                'url': f'/tasks?focus={t.id}',
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
            files = FileAsset.objects.filter(
                Q(name__icontains=query)
            ).select_related('project', 'uploader')[:limit]
            results['files'] = [{
                'id': f.id,
                'name': f.name,
                'level': f.level,
                'level_display': f.get_level_display(),
                'project_name': f.project.name if f.project else '',
                'uploader_name': f.uploader.name if f.uploader else '',
                'url': f'/files?focus={f.id}',
            } for f in files]

        # 搜索比赛
        if 'competitions' in active_modules:
            competitions = Competition.objects.filter(
                Q(name__icontains=query) |
                Q(organizer__icontains=query) |
                Q(comp_type__icontains=query)
            )[:limit]
            results['competitions'] = [{
                'id': c.id,
                'name': c.name,
                'status': c.status,
                'url': f'/competitions?focus={c.id}',
            } for c in competitions]

        # 搜索知识库文章
        if 'knowledge' in active_modules:
            articles = KnowledgeArticle.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__icontains=query)
            ).select_related('author', 'project')[:limit]
            results['knowledge'] = [{
                'id': a.id,
                'title': a.title,
                'category': a.category,
                'category_display': a.get_category_display(),
                'author_name': a.author.name if a.author else '',
                'project_name': a.project.name if a.project else '',
                'tags': a.tags,
                'url': f'/projects/knowledge?focus={a.id}',
            } for a in articles]

        # 搜索讨论主题
        if 'discussions' in active_modules:
            topics = DiscussionTopic.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query)
            ).select_related('project', 'author')[:limit]
            results['discussions'] = [{
                'id': t.id,
                'title': t.title,
                'project_name': t.project.name if t.project else '',
                'author_name': t.author.name if t.author else '',
                'is_pinned': t.is_pinned,
                'is_closed': t.is_closed,
                'reply_count': t.reply_count,
                'url': f'/projects/discussions?focus={t.id}',
            } for t in topics]

        # 总结果数（只计算活跃模块）
        total = sum(len(results[k]) for k in active_modules)

        return success_response({
            **results,
            'total': total,
            'query': query,
            'search_type': search_type_raw or None,
        })
