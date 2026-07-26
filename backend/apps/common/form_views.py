"""
自定义表单序列化器与视图
- CustomFormViewSet: 表单 CRUD
- FormSubmissionViewSet: 提交记录 CRUD + my_submissions
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsTeacherOrAdminOrReadOnly
from .form_models import CustomForm, FormSubmission


# ============ 序列化器 ============

class CustomFormSerializer(serializers.ModelSerializer):
    """自定义表单序列化器"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = CustomForm
        fields = (
            'id', 'name', 'description', 'fields',
            'created_by', 'created_by_name', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')


class CustomFormCreateSerializer(serializers.ModelSerializer):
    """表单创建序列化器"""

    class Meta:
        model = CustomForm
        fields = ('id', 'name', 'description', 'fields', 'is_active')
        read_only_fields = ('id',)


class FormSubmissionSerializer(serializers.ModelSerializer):
    """表单提交序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    form_name = serializers.CharField(source='form.name', read_only=True, default='')

    class Meta:
        model = FormSubmission
        fields = ('id', 'form', 'form_name', 'user', 'user_name', 'data', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')


# ============ ViewSet ============

class CustomFormViewSet(MultiSerializerMixin, ModelViewSet):
    """自定义表单 CRUD"""
    queryset = CustomForm.objects.all().order_by('-created_at')
    serializer_class = CustomFormSerializer
    serializer_classes_by_action = {
        'list': CustomFormSerializer,
        'retrieve': CustomFormSerializer,
        'create': CustomFormCreateSerializer,
        'update': CustomFormCreateSerializer,
        'partial_update': CustomFormCreateSerializer,
    }
    permission_classes = [IsTeacherOrAdminOrReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.global_role in ('teacher', 'sys_admin'):
            return queryset
        return queryset.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = serializer.save(created_by=request.user)
        return success_response(
            CustomFormSerializer(form).data,
            message='表单创建成功',
            http_status=status.HTTP_201_CREATED,
        )


class FormSubmissionViewSet(ModelViewSet):
    """表单提交记录 CRUD"""
    queryset = FormSubmission.objects.all().order_by('-created_at')
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['form', 'user']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().select_related('form', 'user')
        if user.global_role in ('sys_admin', 'teacher'):
            return qs
        return qs.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = serializer.validated_data['form']
        if not form.is_active and request.user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='表单已停用，无法提交',
                code=2601,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        submission = serializer.save(user=request.user)
        return success_response(
            FormSubmissionSerializer(submission).data,
            message='提交成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """我的提交记录"""
        qs = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = FormSubmissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return success_response(FormSubmissionSerializer(qs, many=True).data)
