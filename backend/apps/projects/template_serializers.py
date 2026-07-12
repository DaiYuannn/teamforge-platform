"""
项目模板序列化器
"""
from rest_framework import serializers

from .template_models import ProjectTemplate


class ProjectTemplateSerializer(serializers.ModelSerializer):
    """项目模板序列化器"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = ProjectTemplate
        fields = (
            'id', 'name', 'description', 'category', 'config',
            'created_by', 'created_by_name', 'is_active', 'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')


class ProjectTemplateInstantiateSerializer(serializers.Serializer):
    """项目模板实例化（从模板创建项目）请求序列化器"""
    name = serializers.CharField(max_length=200, help_text='项目名称')
    code = serializers.CharField(max_length=50, help_text='项目编号（唯一）')
    leader = serializers.IntegerField(help_text='项目负责人用户ID')
    intro = serializers.CharField(required=False, allow_blank=True, default='')
    priority = serializers.CharField(required=False, default='normal')
    start_date = serializers.DateField(required=False, allow_null=True)
    planned_end_date = serializers.DateField(required=False, allow_null=True)
