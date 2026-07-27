"""
Git 集成序列化器与视图
- GitRepositoryViewSet: Git 仓库 CRUD
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from common.response import error_response, success_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsSysAdminOrReadOnly
from .git_models import GitRepository
from .connection_services import IntegrationConnectionError, connect_git_repository


class GitRepositorySerializer(serializers.ModelSerializer):
    """Git 仓库序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = GitRepository
        fields = (
            'id', 'url', 'branch', 'token', 'project', 'project_name',
            'created_by', 'created_by_name', 'is_active', 'created_at', 'updated_at',
            'connection_status', 'last_checked_at', 'last_synced_at',
            'last_error', 'remote_commit',
        )
        read_only_fields = (
            'id', 'created_by', 'connection_status', 'last_checked_at',
            'last_synced_at', 'last_error', 'remote_commit',
            'created_at', 'updated_at',
        )
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

    def _connect(self, repository, *, sync):
        if not repository.is_active:
            return error_response(
                message='Repository connection is disabled', code=1001,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            metadata = connect_git_repository(repository)
        except IntegrationConnectionError as exc:
            repository.record_connection(connected=False, error=str(exc))
            return error_response(
                message=str(exc), code=2502,
                http_status=status.HTTP_502_BAD_GATEWAY,
            )
        repository.record_connection(
            connected=True,
            commit=metadata['commit'],
            synced=sync,
        )
        return success_response(
            GitRepositorySerializer(repository).data,
            message='Repository sync completed' if sync else 'Connection succeeded',
        )

    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        return self._connect(self.get_object(), sync=False)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        return self._connect(self.get_object(), sync=True)
