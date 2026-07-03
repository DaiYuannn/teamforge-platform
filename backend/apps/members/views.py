"""
成员视图
- MemberViewSet: 只读列表+详情，所有认证用户可查看联系方式
- SkillTagViewSet: 技能标签 CRUD（管理员可管理标签）
- MemberSkillViewSet: 成员技能管理（自己管理自己的技能，可查看他人技能）
- FlexibleWorkScheduleViewSet: 灵活工时管理（每半月一次填写）
- MemberDetailView: 获取成员详情（基本信息+技能+灵活工时+项目+任务）
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsSysAdmin
from apps.users.models import User
from .models import SkillTag, MemberSkill, FlexibleWorkSchedule
from .serializers import (
    SkillTagSerializer,
    MemberSkillSerializer,
    FlexibleWorkScheduleSerializer,
    FlexibleWorkScheduleCreateSerializer,
    MemberSerializer,
    MemberListSerializer,
    MemberDetailSerializer,
)


class MemberViewSet(MultiSerializerMixin, ReadOnlyModelViewSet):
    """
    成员管理 ViewSet（只读）
    - list: 所有认证用户可查看成员列表（含联系方式）
    - retrieve: 所有认证用户可查看成员详情（含联系方式和参与项目）
    """
    queryset = User.objects.filter(is_active=True).order_by('-date_joined')

    serializer_classes_by_action = {
        'list': MemberListSerializer,
        'retrieve': MemberSerializer,
    }

    permission_classes = [IsAuthenticated]

    filterset_fields = ['global_role', 'is_student', 'grade', 'major']
    search_fields = ['username', 'name', 'email', 'phone']
    ordering_fields = ['date_joined', 'name']

    def list(self, request, *args, **kwargs):
        """成员列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """成员详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)


class SkillTagViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    技能标签管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 仅管理员可管理
    """
    queryset = SkillTag.objects.all()
    serializer_class = SkillTagSerializer

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsSysAdmin],
        'update': [IsSysAdmin],
        'partial_update': [IsSysAdmin],
        'destroy': [IsSysAdmin],
    }
    permission_classes = [IsAuthenticated]

    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def list(self, request, *args, **kwargs):
        """技能标签列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """技能标签详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """创建技能标签（仅管理员）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return success_response(
            SkillTagSerializer(tag).data,
            message='技能标签创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新技能标签（仅管理员）"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return success_response(SkillTagSerializer(tag).data, message='技能标签更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除技能标签（仅管理员）"""
        instance = self.get_object()
        instance.delete()
        return success_response(message='技能标签删除成功')


class MemberSkillViewSet(MultiSerializerMixin, ModelViewSet):
    """
    成员技能管理 ViewSet
    - list: 当前用户的技能列表
    - create/update: 添加/修改自己的技能
    - by_user: 查看指定用户的技能（所有登录成员可见）
    - retrieve: 查看技能详情
    """
    queryset = MemberSkill.objects.select_related('user', 'skill').all()
    serializer_class = MemberSkillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """默认返回当前用户的技能"""
        if self.action == 'by_user':
            # by_user action 返回指定用户的技能
            return self.queryset
        # 默认只返回当前用户的技能
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """当前用户的技能列表"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """技能详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """添加自己的技能"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 强制设置为当前用户
        serializer.validated_data['user'] = request.user
        # 检查是否已存在
        skill_id = serializer.validated_data.get('skill')
        if MemberSkill.objects.filter(user=request.user, skill=skill_id).exists():
            return error_response(message='您已添加过该技能，请直接修改', code=1007,
                                  http_status=status.HTTP_400_BAD_REQUEST)
        skill = serializer.save()
        return success_response(
            MemberSkillSerializer(skill).data,
            message='技能添加成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """修改自己的技能"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # 权限校验：只能修改自己的技能
        if instance.user_id != request.user.id:
            return error_response(message='只能修改自己的技能', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        # 不允许修改 user 字段
        data = request.data.copy()
        data.pop('user', None)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()
        return success_response(MemberSkillSerializer(skill).data, message='技能修改成功')

    def partial_update(self, request, *args, **kwargs):
        """部分修改自己的技能"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除自己的技能"""
        instance = self.get_object()
        # 权限校验：只能删除自己的技能
        if instance.user_id != request.user.id:
            return error_response(message='只能删除自己的技能', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return success_response(message='技能删除成功')

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """
        查看指定用户的技能（所有登录成员可见）
        GET /api/v1/members/skills/by_user/?user_id=1
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return error_response(message='请提供 user_id 参数')

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        skills = MemberSkill.objects.filter(user=user).select_related('skill')
        serializer = MemberSkillSerializer(skills, many=True)
        return success_response(serializer.data)


class FlexibleWorkScheduleViewSet(MultiSerializerMixin, ModelViewSet):
    """
    灵活工时管理 ViewSet
    - list: 当前用户的灵活工作时间
    - create: 填写（每半月一次，检查 unique_together）
    - current_period: 获取当前半月周期
    - all_latest: 所有成员最新灵活工作时间（所有登录成员可见）
    - by_user: 查看指定用户的灵活工作时间
    """
    queryset = FlexibleWorkSchedule.objects.select_related('user').all()

    serializer_classes_by_action = {
        'list': FlexibleWorkScheduleSerializer,
        'retrieve': FlexibleWorkScheduleSerializer,
        'create': FlexibleWorkScheduleCreateSerializer,
        'update': FlexibleWorkScheduleCreateSerializer,
        'partial_update': FlexibleWorkScheduleCreateSerializer,
    }
    permission_classes = [IsAuthenticated]

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """默认返回当前用户的灵活工时"""
        if self.action in ('all_latest', 'by_user'):
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """当前用户的灵活工作时间列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """灵活工时详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """填写灵活工时（每半月一次）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 检查当前周期是否已填写
        period_start = serializer.validated_data.get('period_start')
        if FlexibleWorkSchedule.objects.filter(
            user=request.user, period_start=period_start
        ).exists():
            return error_response(
                message='当前周期已填写灵活工作时间，请勿重复填写',
                code=1007,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        schedule = serializer.save()
        return success_response(
            FlexibleWorkScheduleSerializer(schedule).data,
            message='灵活工作时间填写成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """修改自己的灵活工时"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # 权限校验：只能修改自己的灵活工时
        if instance.user_id != request.user.id:
            return error_response(message='只能修改自己的灵活工作时间', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        # 不允许修改 user 字段
        data = request.data.copy()
        data.pop('user', None)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        return success_response(
            FlexibleWorkScheduleSerializer(schedule).data,
            message='灵活工作时间更新成功',
        )

    def partial_update(self, request, *args, **kwargs):
        """部分修改自己的灵活工时"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除自己的灵活工时"""
        instance = self.get_object()
        if instance.user_id != request.user.id:
            return error_response(message='只能删除自己的灵活工作时间', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return success_response(message='灵活工作时间删除成功')

    @action(detail=False, methods=['get'])
    def current_period(self, request):
        """
        获取当前半月周期
        GET /api/v1/members/work-schedules/current_period/
        返回当前半月周期的起止日期及当前用户是否已填写
        """
        today = timezone.now().date()
        if today.day <= 15:
            period_start = today.replace(day=1)
            period_end = (period_start + timedelta(days=15))
        else:
            period_start = today.replace(day=16)
            # 计算月末
            if today.month == 12:
                period_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                period_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        # 检查当前用户是否已填写
        filled = FlexibleWorkSchedule.objects.filter(
            user=request.user, period_start=period_start
        ).first()

        result = {
            'period_start': period_start,
            'period_end': period_end,
            'is_filled': filled is not None,
        }
        if filled:
            result['schedule'] = FlexibleWorkScheduleSerializer(filled).data
        return success_response(result)

    @action(detail=False, methods=['get'])
    def all_latest(self, request):
        """
        所有成员最新灵活工作时间（所有登录成员可见）
        GET /api/v1/members/work-schedules/all_latest/
        返回每个成员最新的一条灵活工时记录
        """
        # 获取所有活跃用户的最新灵活工时
        users = User.objects.filter(is_active=True).order_by('name')
        result = []
        for user in users:
            schedule = FlexibleWorkSchedule.objects.filter(user=user).first()
            if schedule:
                result.append(FlexibleWorkScheduleSerializer(schedule).data)
        return success_response(result)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """
        查看指定用户的灵活工作时间（所有登录成员可见）
        GET /api/v1/members/work-schedules/by_user/?user_id=1
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return error_response(message='请提供 user_id 参数')

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        schedules = FlexibleWorkSchedule.objects.filter(user=user).select_related('user')
        serializer = FlexibleWorkScheduleSerializer(schedules, many=True)
        return success_response(serializer.data)


class MemberDetailView(APIView):
    """
    成员详情视图
    GET /api/v1/members/detail/?user_id=1
    返回成员基本信息 + 技能列表 + 灵活工作时间 + 参与项目 + 任务
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取成员详情"""
        user_id = request.query_params.get('user_id') or request.user.id

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        serializer = MemberDetailSerializer(user)
        return success_response(serializer.data)
