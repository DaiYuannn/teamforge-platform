"""
任务依赖关系序列化器
"""
from rest_framework import serializers

from .dependency_models import TaskDependency


class TaskDependencySerializer(serializers.ModelSerializer):
    """任务依赖关系序列化器"""
    task_title = serializers.CharField(source='task.title', read_only=True)
    depends_on_title = serializers.CharField(source='depends_on.title', read_only=True)

    class Meta:
        model = TaskDependency
        fields = (
            'id', 'task', 'task_title',
            'depends_on', 'depends_on_title',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate(self, attrs):
        """校验：禁止自依赖"""
        task = attrs.get('task') or getattr(self.instance, 'task', None)
        depends_on = attrs.get('depends_on') or getattr(self.instance, 'depends_on', None)
        if task and depends_on and task == depends_on:
            raise serializers.ValidationError('任务不能依赖自身')
        return attrs
