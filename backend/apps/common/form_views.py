"""
自定义表单序列化器与视图
- CustomFormViewSet: 表单 CRUD
- FormSubmissionViewSet: 提交记录 CRUD + my_submissions
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.utils.dateparse import parse_date
import re

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsTeacherOrAdminOrReadOnly
from .form_models import CustomForm, FormSubmission


FORM_FIELD_TYPES = {'text', 'textarea', 'number', 'date', 'select', 'switch'}


def validate_form_fields(fields):
    if not isinstance(fields, list):
        raise serializers.ValidationError('fields must be a list')
    normalized = []
    seen = set()
    for index, raw in enumerate(fields):
        if not isinstance(raw, dict):
            raise serializers.ValidationError(f'Field {index + 1} must be an object')
        field = dict(raw)
        key = str(field.get('key') or field.get('name') or '').strip()
        field_type = field.get('type')
        if not key or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', key):
            raise serializers.ValidationError(f'Field {index + 1} has an invalid key')
        if key in seen:
            raise serializers.ValidationError(f'Duplicate field key: {key}')
        if field_type not in FORM_FIELD_TYPES:
            raise serializers.ValidationError(f'Unsupported type for field {key}')
        if field_type == 'select':
            options = field.get('options')
            if not isinstance(options, list) or not options:
                raise serializers.ValidationError(f'Select field {key} requires options')
            if any(isinstance(option, (dict, list)) for option in options):
                raise serializers.ValidationError(f'Select field {key} has invalid options')
        if field_type in {'text', 'textarea'}:
            try:
                min_length = int(field.get('min_length', 0))
                max_length = int(field.get('max_length', 1000000))
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    f'Text field {key} has invalid length limits'
                ) from exc
            if min_length < 0 or max_length < min_length:
                raise serializers.ValidationError(
                    f'Text field {key} has invalid length limits'
                )
            if field.get('pattern'):
                try:
                    re.compile(str(field['pattern']))
                except re.error as exc:
                    raise serializers.ValidationError(
                        f'Text field {key} has an invalid pattern'
                    ) from exc
        if field_type == 'number':
            try:
                minimum = float(field.get('min', '-inf'))
                maximum = float(field.get('max', 'inf'))
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    f'Number field {key} has invalid limits'
                ) from exc
            if maximum < minimum:
                raise serializers.ValidationError(
                    f'Number field {key} has invalid limits'
                )
        field['key'] = key
        seen.add(key)
        normalized.append(field)
    return normalized


def validate_submission_data(form, data):
    if not isinstance(data, dict):
        raise serializers.ValidationError({'data': 'Submission data must be an object'})
    fields = validate_form_fields(form.fields)
    definitions = {field['key']: field for field in fields}
    errors = {}
    unknown = sorted(set(data) - set(definitions))
    if unknown:
        errors['_unknown'] = f'Unknown fields: {", ".join(unknown)}'
    for key, field in definitions.items():
        value = data.get(key)
        empty = value is None or value == ''
        if field.get('required') and empty:
            errors[key] = 'This field is required'
            continue
        if empty:
            continue
        field_type = field['type']
        if field_type in {'text', 'textarea'}:
            if not isinstance(value, str):
                errors[key] = 'Must be text'
                continue
            if field.get('min_length') is not None and len(value) < int(field['min_length']):
                errors[key] = f'Minimum length is {field["min_length"]}'
            if field.get('max_length') is not None and len(value) > int(field['max_length']):
                errors[key] = f'Maximum length is {field["max_length"]}'
            if field.get('pattern') and not re.fullmatch(str(field['pattern']), value):
                errors[key] = 'Invalid format'
        elif field_type == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors[key] = 'Must be a number'
                continue
            if field.get('min') is not None and value < float(field['min']):
                errors[key] = f'Minimum value is {field["min"]}'
            if field.get('max') is not None and value > float(field['max']):
                errors[key] = f'Maximum value is {field["max"]}'
        elif field_type == 'date' and (not isinstance(value, str) or parse_date(value) is None):
            errors[key] = 'Must be an ISO date'
        elif field_type == 'select' and value not in field.get('options', []):
            errors[key] = 'Must be one of the configured options'
        elif field_type == 'switch' and not isinstance(value, bool):
            errors[key] = 'Must be true or false'
    if errors:
        raise serializers.ValidationError({'data': errors})
    return data


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

    def validate_fields(self, value):
        return validate_form_fields(value)


class CustomFormCreateSerializer(serializers.ModelSerializer):
    """表单创建序列化器"""

    class Meta:
        model = CustomForm
        fields = ('id', 'name', 'description', 'fields', 'is_active')
        read_only_fields = ('id',)

    def validate_fields(self, value):
        return validate_form_fields(value)


class FormSubmissionSerializer(serializers.ModelSerializer):
    """表单提交序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    form_name = serializers.CharField(source='form.name', read_only=True, default='')

    class Meta:
        model = FormSubmission
        fields = ('id', 'form', 'form_name', 'user', 'user_name', 'data', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        form = attrs.get('form') or getattr(self.instance, 'form', None)
        if form:
            attrs['data'] = validate_submission_data(form, attrs.get('data', {}))
        return attrs


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
