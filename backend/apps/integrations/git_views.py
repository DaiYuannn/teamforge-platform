"""
Git 集成序列化器与视图
- GitRepositoryViewSet: Git 仓库 CRUD
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsSysAdminOrReadOnly
from .git_models import GitRepository


class GitRepositorySerializer(serializers.ModelSerializer):
    """Git 仓库序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = GitRepository
        fields = (
            'id', 'url', 'branch', 'token', 'project', 'project_name',
            'created_by', 'created_by_name', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')
        extra_kwargs = {'token': {'write_only': True, 'required': False, 'allow_blank': True}}


class GitRepositoryViewSet(MultiSerializerMixin, ModelViewSet):
    """Git 仓库 CRUD"""
    queryset = GitRepository.objects.all().order_by('-created_at')
    serializer_class = GitRepositorySerializer
    serializer_classes_by_action = {
        'list': GitRepositorySerializer,
        'retrieve': GitRepositorySerializer,
        'create': GitRepositorySerializer,
        'update': GitRepositorySerializer,
        'partial_update': GitRepositorySerializer,
    }
    permission_classes = [IsAuthenticated, IsSysAdminOrReadOnly]
    filterset_fields = ['project', 'is_active']
    search_fields = ['url', 'branch']
    ordering_fields = ['created_at', 'updated_at']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repo = serializer.save(created_by=request.user)
        return success_response(
            GitRepositorySerializer(repo).data,
            message='Git 仓库创建成功',
            http_status=status.HTTP_201_CREATED,
        )
