"""
文件序列化器
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import FileAsset, FileFolder, FileVersion
from .tag_models import FileTag, FileTagRelation


class FileTagSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    color = serializers.CharField()


class FileVersionSerializer(serializers.ModelSerializer):
    """文件版本序列化器"""
    uploader_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    file = serializers.FileField(write_only=True)

    class Meta:
        model = FileVersion
        fields = ('id', 'file_asset', 'file', 'version', 'uploader', 'uploader_name', 'created_at')
        read_only_fields = ('id', 'uploader', 'created_at')


class FileAssetSerializer(serializers.ModelSerializer):
    """文件资源序列化器"""
    file = serializers.FileField(write_only=True)
    uploader_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    folder_name = serializers.CharField(source='folder.name', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    competition_entry_name = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = FileAsset
        fields = (
            'id', 'project', 'project_name', 'folder', 'folder_name',
            'team', 'team_name', 'competition_entry', 'competition_entry_name',
            'name', 'file', 'file_url',
            'level', 'level_display', 'size', 'content_type',
            'uploader', 'uploader_name', 'version',
            'file_hash', 'watermark_text', 'can_manage', 'tags',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'size', 'content_type', 'uploader', 'version', 'file_hash', 'created_at', 'updated_at')
        extra_kwargs = {
            'name': {'required': False},
            'folder': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        project = attrs.get('project', getattr(self.instance, 'project', None))
        folder = attrs.get('folder', getattr(self.instance, 'folder', None))
        team = attrs.get('team', getattr(self.instance, 'team', None))
        competition = attrs.get(
            'competition_entry',
            getattr(self.instance, 'competition_entry', None),
        )
        level = attrs.get('level', getattr(self.instance, 'level', FileAsset.Level.PUBLIC))
        if team and competition:
            raise serializers.ValidationError({
                'team': '指定小团队与指定比赛参赛条目不能同时设置',
            })
        if level == FileAsset.Level.PUBLIC and (team or competition):
            raise serializers.ValidationError({
                'level': '公开文件不能再设置小团队或比赛条目范围',
            })
        if competition:
            if project and competition.project_id != project.id:
                raise serializers.ValidationError({
                    'competition_entry': '参赛条目必须属于文件所在项目',
                })
            if project is None:
                project = competition.project
                attrs['project'] = project
        if team and project:
            from common.project_access import project_root_team_ids

            team_root_id = team.parent_id or team.id
            project_roots = project_root_team_ids(project)
            if project_roots and team_root_id not in project_roots:
                raise serializers.ValidationError({
                    'team': '指定团队必须与文件所在项目属于同一组织范围',
                })
        if folder and folder.project_id != getattr(project, 'id', None):
            raise serializers.ValidationError({
                'folder': '文件夹必须属于文件所在项目',
            })
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .permissions import user_can_manage_file_scope

            if not user_can_manage_file_scope(
                request.user,
                project=project,
                team=team,
                competition_entry=competition,
            ):
                raise serializers.ValidationError('无权写入所选文件可见范围')
        return attrs

    def get_competition_entry_name(self, obj):
        if not obj.competition_entry_id:
            return ''
        competition = obj.competition_entry
        return competition.entry_name or competition.name

    def get_can_manage(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from .permissions import user_can_manage_file_scope

        return user_can_manage_file_scope(
            request.user,
            project=obj.project,
            team=obj.team,
            competition_entry=obj.competition_entry,
        )

    @extend_schema_field(FileTagSummarySerializer(many=True))
    def get_tags(self, obj):
        return [
            {'id': relation.tag_id, 'name': relation.tag.name, 'color': relation.tag.color}
            for relation in obj.tag_relations.all()
        ]

    def get_file_url(self, obj) -> str | None:
        """获取文件访问URL"""
        if obj.level == FileAsset.Level.SENSITIVE:
            return None
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def to_representation(self, instance):
        """敏感文件响应中不生成、也不返回任何签名文件地址。"""
        data = super().to_representation(instance)
        if instance.level == FileAsset.Level.SENSITIVE:
            data.pop('file_url', None)
        return data


class FileAssetListSerializer(serializers.ModelSerializer):
    """文件资源列表精简序列化器"""
    uploader_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    competition_entry_name = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    deleted_by_name = serializers.CharField(source='deleted_by.name', read_only=True, default='')
    tags = serializers.SerializerMethodField()

    class Meta:
        model = FileAsset
        fields = (
            'id', 'project', 'project_name', 'folder', 'folder_name',
            'team', 'team_name', 'competition_entry', 'competition_entry_name', 'name',
            'level', 'level_display', 'size', 'content_type',
            'uploader_name', 'version', 'file_hash', 'watermark_text',
            'can_manage', 'tags',
            'created_at', 'deleted_at', 'deleted_by_name',
        )
        read_only_fields = fields

    @extend_schema_field(FileTagSummarySerializer(many=True))
    def get_tags(self, obj):
        return [
            {'id': relation.tag_id, 'name': relation.tag.name, 'color': relation.tag.color}
            for relation in obj.tag_relations.all()
        ]

    def get_competition_entry_name(self, obj):
        if not obj.competition_entry_id:
            return ''
        competition = obj.competition_entry
        return competition.entry_name or competition.name

    def get_can_manage(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from .permissions import user_can_manage_file_scope

        return user_can_manage_file_scope(
            request.user,
            project=obj.project,
            team=obj.team,
            competition_entry=obj.competition_entry,
        )


class FileFolderSerializer(serializers.ModelSerializer):
    """项目文件夹序列化器。"""

    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    parent_name = serializers.CharField(source='parent.name', read_only=True, default='')
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    file_count = serializers.IntegerField(read_only=True, default=0)
    path = serializers.SerializerMethodField()

    class Meta:
        model = FileFolder
        fields = (
            'id', 'project', 'project_name', 'name', 'parent', 'parent_name',
            'path', 'file_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'created_by', 'created_at', 'updated_at', 'file_count',
        )
        extra_kwargs = {
            'parent': {'required': False, 'allow_null': True, 'default': None},
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('文件夹名称不能为空')
        return value

    def validate(self, attrs):
        project = attrs.get('project', getattr(self.instance, 'project', None))
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        name = attrs.get('name', getattr(self.instance, 'name', ''))
        if parent and parent.project_id != getattr(project, 'id', None):
            raise serializers.ValidationError({'parent': '上级文件夹必须属于同一项目'})
        ancestor = parent
        depth = 1
        while ancestor is not None:
            if self.instance and ancestor.pk == self.instance.pk:
                raise serializers.ValidationError({
                    'parent': '文件夹不能移动到自身或子文件夹中',
                })
            depth += 1
            if depth > 8:
                raise serializers.ValidationError({'parent': '文件夹层级不能超过 8 层'})
            ancestor = ancestor.parent

        duplicates = FileFolder.objects.filter(
            project=project,
            parent=parent,
            name=name,
        )
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({'name': '同级目录下已存在同名文件夹'})
        return attrs

    def get_path(self, obj) -> str:
        names = [obj.name]
        ancestor = obj.parent
        while ancestor is not None and len(names) < 8:
            names.append(ancestor.name)
            ancestor = ancestor.parent
        return ' / '.join(reversed(names))


class MoveFileSerializer(serializers.Serializer):
    folder = serializers.PrimaryKeyRelatedField(
        queryset=FileFolder.objects.all(),
        required=False,
        allow_null=True,
    )


class FileTagSerializer(serializers.ModelSerializer):
    """文件标签序列化器"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')

    class Meta:
        model = FileTag
        fields = (
            'id', 'name', 'color', 'project', 'project_name',
            'created_by', 'created_by_name', 'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')
        extra_kwargs = {
            # project 允许为空（全局标签），显式声明非必填
            'project': {'required': False, 'allow_null': True},
        }
        # 清除自动生成的 UniqueTogetherValidator：它会把 unique_together 中的
        # project 字段强制变为必填，与"全局标签 project 可为空"的需求冲突。
        # 唯一性约束仍由数据库层面的 unique_together 保证。
        validators = []


class FileTagRelationSerializer(serializers.ModelSerializer):
    """文件-标签关联序列化器"""
    tag_name = serializers.CharField(source='tag.name', read_only=True, default='')
    tag_color = serializers.CharField(source='tag.color', read_only=True, default='')
    file_name = serializers.CharField(source='file.name', read_only=True, default='')

    class Meta:
        model = FileTagRelation
        fields = (
            'id', 'file', 'file_name', 'tag', 'tag_name', 'tag_color', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class AssignTagsSerializer(serializers.Serializer):
    """分配/取消标签请求序列化器"""
    file = serializers.IntegerField(help_text='文件ID')
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='标签ID列表',
    )
