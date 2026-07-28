"""
通知序列化器
"""
from rest_framework import serializers

from common.project_access import active_user_root_team_ids
from apps.common.team_models import Team

from .models import Notification, Announcement
from .announcement_access import (
    announcement_management_scope,
    announcement_is_manageable_from_scope,
)


class NotificationListSerializer(serializers.ModelSerializer):
    """通知列表精简序列化器"""
    # 接收人姓名
    recipient_name = serializers.CharField(source='recipient.name', read_only=True, default='')
    # 发送人姓名
    sender_name = serializers.CharField(source='sender.name', read_only=True, default='')
    # 通知类型显示
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    # 优先级显示
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )
    # 渠道显示
    channel_display = serializers.CharField(
        source='get_channel_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'recipient_name', 'sender', 'sender_name',
            'title', 'content', 'notification_type', 'notification_type_display',
            'priority', 'priority_display', 'channel', 'channel_display',
            'email_delivery_status', 'email_digest_frequency',
            'email_attempted_at', 'email_sent_at', 'email_delivery_error',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        )
        read_only_fields = fields


class AnnouncementSerializer(serializers.ModelSerializer):
    """公告序列化器"""
    # 类别显示
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    # 状态显示
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    audience_display = serializers.CharField(
        source='get_audience_display', read_only=True
    )
    # 发布人姓名
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True,
        default='',
    )
    target_team_names = serializers.SlugRelatedField(
        source='target_teams',
        many=True,
        read_only=True,
        slug_field='name',
    )
    target_project_names = serializers.SlugRelatedField(
        source='target_projects',
        many=True,
        read_only=True,
        slug_field='name',
    )
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'content', 'resource_links',
            'category', 'category_display',
            'status', 'status_display',
            'audience', 'audience_display',
            'organization', 'organization_name',
            'target_teams', 'target_team_names',
            'target_projects', 'target_project_names',
            'is_pinned', 'is_public', 'can_manage',
            'author', 'author_name', 'published_at',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'category_display', 'status_display', 'audience_display',
            'organization_name', 'target_team_names', 'target_project_names',
            'can_manage', 'author', 'author_name', 'published_at',
            'created_at', 'updated_at',
        )

    def get_can_manage(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        cache_key = '_announcement_management_scope'
        scope = self.context.get(cache_key)
        if scope is None:
            scope = announcement_management_scope(request.user)
            self.context[cache_key] = scope
        return announcement_is_manageable_from_scope(
            obj,
            request.user,
            scope,
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        instance = self.instance

        audience_supplied = 'audience' in self.initial_data
        public_supplied = 'is_public' in self.initial_data
        audience = attrs.get(
            'audience',
            getattr(instance, 'audience', Announcement.Audience.ORGANIZATION),
        )
        if not audience_supplied and public_supplied:
            audience = (
                Announcement.Audience.PUBLIC
                if attrs.get('is_public')
                else Announcement.Audience.ORGANIZATION
            )
            attrs['audience'] = audience
        attrs['is_public'] = audience == Announcement.Audience.PUBLIC

        target_teams = attrs.get('target_teams')
        if target_teams is None:
            target_teams = list(instance.target_teams.all()) if instance else []
        target_projects = attrs.get('target_projects')
        if target_projects is None:
            target_projects = list(instance.target_projects.all()) if instance else []

        if audience != Announcement.Audience.TEAMS:
            target_teams = []
            attrs['target_teams'] = []
        if audience != Announcement.Audience.PROJECTS:
            target_projects = []
            attrs['target_projects'] = []

        if audience == Announcement.Audience.TEAMS and not target_teams:
            raise serializers.ValidationError({
                'target_teams': '指定小团队范围至少需要选择一个小团队'
            })
        if audience == Announcement.Audience.PROJECTS and not target_projects:
            raise serializers.ValidationError({
                'target_projects': '指定项目范围至少需要选择一个项目'
            })

        organization = attrs.get(
            'organization',
            getattr(instance, 'organization', None),
        )
        inferred_root_ids = {
            team.parent_id or team.id
            for team in target_teams
        }
        for project in target_projects:
            inferred_root_ids.update(
                parent_id or team_id
                for team_id, parent_id in project.teams.values_list(
                    'id',
                    'parent_id',
                )
            )
        if organization is None and len(inferred_root_ids) == 1:
            organization = Team.objects.filter(
                pk=next(iter(inferred_root_ids)),
            ).first()
        user_root_ids = active_user_root_team_ids(user)
        if organization is None and len(user_root_ids) == 1:
            organization = Team.objects.filter(pk=next(iter(user_root_ids))).first()

        active_root_ids = set(
            Team.objects.filter(
                parent__isnull=True,
                is_active=True,
            ).values_list('id', flat=True)
        )
        if active_root_ids:
            if organization is None:
                raise serializers.ValidationError({
                    'organization': '请选择公告所属的实践团队'
                })
            if organization.parent_id:
                raise serializers.ValidationError({
                    'organization': '所属实践团队必须选择总团队，不能选择小团队'
                })
            if organization.id not in user_root_ids:
                raise serializers.ValidationError({
                    'organization': '不能向其他实践团队发布或移动公告'
                })
            if inferred_root_ids and inferred_root_ids != {organization.id}:
                raise serializers.ValidationError(
                    '目标小团队或项目必须全部属于所选实践团队'
                )
        attrs['organization'] = organization

        if audience == Announcement.Audience.TEAMS:
            invalid_teams = [
                team for team in target_teams
                if not team.parent_id or team.parent_id != organization.id
            ]
            if invalid_teams:
                raise serializers.ValidationError({
                    'target_teams': '只能选择所属实践团队下的具体小团队'
                })

        management_scope = announcement_management_scope(user)
        if not management_scope['legacy_global']:
            if audience in {
                Announcement.Audience.ORGANIZATION,
                Announcement.Audience.PUBLIC,
            } and organization.id not in management_scope['root_ids']:
                raise serializers.ValidationError({
                    'audience': '只有总团队负责人或团队公告管理员可以选择该范围'
                })
            if (
                audience == Announcement.Audience.TEAMS
                and not {team.id for team in target_teams}.issubset(
                    management_scope['team_ids']
                )
            ):
                raise serializers.ValidationError({
                    'target_teams': '只能向自己负责的小团队发布公告'
                })
            if (
                audience == Announcement.Audience.PROJECTS
                and not {project.id for project in target_projects}.issubset(
                    management_scope['project_ids']
                )
            ):
                raise serializers.ValidationError({
                    'target_projects': '只能向自己负责的项目发布公告'
                })
        return attrs

    def validate_resource_links(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('资源链接必须是列表')
        if len(value) > 20:
            raise serializers.ValidationError('一条公告最多添加 20 个资源链接')

        normalized = []
        url_field = serializers.URLField(max_length=500)
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源链接格式不正确'
                )
            title = str(item.get('title') or '').strip()
            url = str(item.get('url') or '').strip()
            if not title or not url:
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源链接需填写名称和网址'
                )
            if len(title) > 100:
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源名称不能超过 100 字'
                )
            if not url.lower().startswith(('http://', 'https://')):
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源链接仅支持 http/https'
                )
            normalized.append({
                'title': title,
                'url': url_field.run_validation(url),
            })
        return normalized


class NotificationSerializer(serializers.ModelSerializer):
    """通知完整序列化器（详情）"""
    # 接收人姓名
    recipient_name = serializers.CharField(source='recipient.name', read_only=True, default='')
    # 发送人姓名
    sender_name = serializers.CharField(source='sender.name', read_only=True, default='')
    # 通知类型显示
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    # 优先级显示
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )
    # 渠道显示
    channel_display = serializers.CharField(
        source='get_channel_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'recipient_name', 'sender', 'sender_name',
            'title', 'content', 'notification_type', 'notification_type_display',
            'priority', 'priority_display', 'channel', 'channel_display',
            'email_delivery_status', 'email_digest_frequency',
            'email_attempted_at', 'email_sent_at', 'email_delivery_error',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        )
        read_only_fields = fields
