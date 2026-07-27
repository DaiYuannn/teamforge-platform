"""
用户视图
- UserViewSet: 用户管理（管理员增删改查）
- MyProfileView: 当前用户个人信息
- LoginView: 登录获取 token
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from datetime import timedelta
import logging
from django.db import transaction
from django.utils import timezone

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.schema import success_response_schema
from .models import User, UserLifecycleEvent
from .serializers import (
    UserSerializer, UserListSerializer, UserCreateSerializer,
    UserUpdateSerializer, MyProfileSerializer, LoginSerializer,
    UserLifecycleEventSerializer,
)
from .permissions import IsUserManager, IsSelfOrAdmin
from .login_security_services import (
    get_client_ip, get_user_agent, is_ip_blocked, record_login_attempt,
)


logger = logging.getLogger(__name__)


class UserViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    用户管理 ViewSet
    - list/retrieve: 老师/管理员可查看
    - create/update/destroy: 仅管理员
    """
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsUserManager]

    serializer_classes_by_action = {
        'list': UserListSerializer,
        'retrieve': UserSerializer,
        'create': UserCreateSerializer,
        'update': UserUpdateSerializer,
        'partial_update': UserUpdateSerializer,
    }

    permission_classes_by_action = {
        'list': [IsUserManager],
        'retrieve': [IsUserManager],
        'create': [IsUserManager],
        'update': [IsUserManager],
        'partial_update': [IsUserManager],
        'destroy': [IsUserManager],
    }

    filterset_fields = [
        'global_role', 'membership_status', 'is_student', 'is_active', 'grade', 'major'
    ]
    search_fields = ['username', 'email', 'name', 'phone']
    ordering_fields = ['date_joined', 'name', 'email']

    def create(self, request, *args, **kwargs):
        """创建用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserLifecycleEvent.objects.create(
            user=user,
            event_type=UserLifecycleEvent.EventType.CREATED,
            to_status=user.membership_status,
            to_role=user.global_role,
            operator=request.user,
        )
        return success_response(
            UserSerializer(user).data,
            message='用户创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新用户"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_role = instance.global_role
        old_status = instance.membership_status
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if old_role != user.global_role or old_status != user.membership_status:
            UserLifecycleEvent.objects.create(
                user=user,
                event_type=(
                    UserLifecycleEvent.EventType.ROLE_CHANGED
                    if old_role != user.global_role and old_status == user.membership_status
                    else UserLifecycleEvent.EventType.STATUS_CHANGED
                ),
                from_status=old_status,
                to_status=user.membership_status,
                from_role=old_role,
                to_role=user.global_role,
                operator=request.user,
            )
        return success_response(UserSerializer(user).data, message='用户更新成功')

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """成员退出团队：停用账号但保留全部历史数据。"""
        instance = self.get_object()
        if instance.id == request.user.id:
            return error_response(message='不能删除当前登录用户', code=1007)
        self._transition_membership(
            instance,
            status_value=User.MembershipStatus.EXITED,
            reason=request.data.get('reason', '管理员执行离队'),
            handover_to_id=request.data.get('handover_to'),
            handover_notes=request.data.get('handover_notes', ''),
            operator=request.user,
        )
        return success_response(message='成员已离队，账号及历史记录已保留')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def transition(self, request, pk=None):
        """变更成员生命周期状态，并同步团队/项目中的活动关系。"""
        user = self.get_object()
        if user.id == request.user.id and request.data.get('status') == User.MembershipStatus.EXITED:
            return error_response(message='不能将当前登录用户设为离队', code=1007)
        status_value = request.data.get('status')
        if status_value not in User.MembershipStatus.values:
            return error_response(
                message=f'成员状态不合法，可选值：{list(User.MembershipStatus.values)}',
                code=1001,
            )
        self._transition_membership(
            user,
            status_value=status_value,
            reason=request.data.get('reason', ''),
            handover_to_id=request.data.get('handover_to'),
            handover_notes=request.data.get('handover_notes', ''),
            operator=request.user,
        )
        return success_response(UserSerializer(user).data, message='成员状态已更新')

    @action(detail=True, methods=['get'])
    def lifecycle(self, request, pk=None):
        user = self.get_object()
        records = user.lifecycle_events.select_related('operator', 'handover_to').all()
        return success_response(UserLifecycleEventSerializer(records, many=True).data)

    @staticmethod
    def _transition_membership(user, status_value, reason, handover_to_id, handover_notes, operator):
        handover_to = None
        if handover_to_id:
            handover_to = User.objects.exclude(pk=user.pk).filter(pk=handover_to_id).first()
            if handover_to is None:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'handover_to': '交接人不存在或不能是本人'})

        old_status = user.membership_status
        user.membership_status = status_value
        user.exit_reason = reason if status_value == User.MembershipStatus.EXITED else ''
        user.handover_to = handover_to
        user.handover_notes = handover_notes
        if status_value == User.MembershipStatus.EXITED:
            user.team_left_at = timezone.now()
            user.is_active = False
        elif status_value == User.MembershipStatus.ACTIVE:
            user.team_left_at = None
            user.is_active = True
        user.save()

        event_type = (
            UserLifecycleEvent.EventType.REACTIVATED
            if old_status == User.MembershipStatus.EXITED and status_value == User.MembershipStatus.ACTIVE
            else UserLifecycleEvent.EventType.STATUS_CHANGED
        )
        UserLifecycleEvent.objects.create(
            user=user,
            event_type=event_type,
            from_status=old_status,
            to_status=status_value,
            from_role=user.global_role,
            to_role=user.global_role,
            reason=reason,
            handover_to=handover_to,
            handover_notes=handover_notes,
            operator=operator,
        )

        # 退出时保留关系行，只把当前活动关系标为退出并写入各自历史。
        if status_value == User.MembershipStatus.EXITED:
            from apps.common.team_models import TeamMember, TeamMembershipEvent
            from apps.projects.models import ProjectMember, ProjectMembershipEvent

            for membership in TeamMember.objects.filter(user=user, status=TeamMember.Status.ACTIVE):
                target = (
                    TeamMember.objects.filter(
                        team=membership.team,
                        user=handover_to,
                        status=TeamMember.Status.ACTIVE,
                    ).first()
                    if handover_to else None
                )
                membership.status = TeamMember.Status.EXITED
                membership.left_at = timezone.now()
                membership.exit_reason = reason
                membership.handover_to = target
                membership.handover_notes = handover_notes
                membership.save()
                TeamMembershipEvent.objects.create(
                    membership=membership,
                    event_type='exited',
                    from_role=membership.role,
                    to_role=membership.role,
                    from_status=TeamMember.Status.ACTIVE,
                    to_status=TeamMember.Status.EXITED,
                    reason=reason,
                    handover_to=target,
                    handover_notes=handover_notes,
                    operator=operator,
                )

            for membership in ProjectMember.objects.filter(
                user=user, status=ProjectMember.Status.ACTIVE
            ):
                target = (
                    ProjectMember.objects.filter(
                        project=membership.project,
                        user=handover_to,
                        status=ProjectMember.Status.ACTIVE,
                    ).first()
                    if handover_to else None
                )
                # 项目负责人不能悄悄离队：必须先把项目负责人转给交接人。
                if membership.project.leader_id == user.id:
                    if target is None:
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({
                            'handover_to': f'成员负责项目“{membership.project.name}”，需指定该项目中的活动成员进行交接'
                        })
                    membership.project.leader = handover_to
                    membership.project.save(update_fields=['leader', 'updated_at'])
                    target.role_in_project = ProjectMember.RoleInProject.LEADER
                    target.save(update_fields=['role_in_project'])
                membership.status = ProjectMember.Status.EXITED
                membership.exited_at = timezone.now()
                membership.exit_reason = reason
                membership.handover_to = target
                membership.handover_notes = handover_notes
                membership.save()
                ProjectMembershipEvent.objects.create(
                    membership=membership,
                    event_type=ProjectMembershipEvent.EventType.EXITED,
                    from_role=membership.role_in_project,
                    to_role=membership.role_in_project,
                    from_status=ProjectMember.Status.ACTIVE,
                    to_status=ProjectMember.Status.EXITED,
                    reason=reason,
                    handover_to=target,
                    handover_notes=handover_notes,
                    operator=operator,
                )


class MyProfileView(RetrieveUpdateAPIView):
    """
    当前用户个人信息
    - GET: 获取当前用户信息
    - PUT/PATCH: 修改当前用户个人信息
    """
    serializer_class = MyProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(MyProfileSerializer(user).data, message='个人信息更新成功')


class LoginView(APIView):
    """
    登录视图
    - POST: 邮箱+密码登录，返回 token + 用户信息
    - 记录登录尝试，IP 连续失败自动封禁
    """
    permission_classes = []

    @extend_schema(
        auth=[],
        request=LoginSerializer,
        responses={
            200: success_response_schema(
                'LoginResponse',
                inline_serializer(
                    name='LoginData',
                    fields={
                        'token': inline_serializer(
                            name='JWTTokenPair',
                            fields={
                                'access': serializers.CharField(),
                                'refresh': serializers.CharField(),
                            },
                        ),
                        'user': UserSerializer(),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        remember_me = serializer.validated_data['remember_me']

        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # IP 封禁检查
        if is_ip_blocked(ip_address):
            record_login_attempt(
                email=email, ip_address=ip_address, user_agent=user_agent,
                is_success=False, failure_reason='IP 已被封禁',
            )
            return error_response(message='该 IP 已被临时封禁，请稍后再试', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)

        # 通过 email 查找用户并验证密码
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            record_login_attempt(
                email=email, ip_address=ip_address, user_agent=user_agent,
                is_success=False, failure_reason='用户不存在',
            )
            return error_response(message='邮箱或密码错误', code=1001,
                                  http_status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            record_login_attempt(
                email=email, ip_address=ip_address, user_agent=user_agent,
                is_success=False, failure_reason='密码错误',
            )
            return error_response(message='邮箱或密码错误', code=1001,
                                  http_status=status.HTTP_401_UNAUTHORIZED)

        if (
            not user.is_active
            or user.membership_status == User.MembershipStatus.EXITED
        ):
            record_login_attempt(
                email=email, ip_address=ip_address, user_agent=user_agent,
                is_success=False, failure_reason='账号已禁用或已退出团队',
            )
            return error_response(message='账号已退出团队或已被禁用，请联系管理员', code=1002,
                                  http_status=status.HTTP_403_FORBIDDEN)

        # 登录成功，记录成功尝试
        record_login_attempt(
            email=email, ip_address=ip_address, user_agent=user_agent,
            is_success=True, failure_reason='',
        )

        # 生成 JWT token
        refresh = RefreshToken.for_user(user)
        refresh.set_exp(lifetime=(
            timedelta(days=30) if remember_me else timedelta(days=1)
        ))

        return success_response({
            'token': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'user': UserSerializer(user).data,
        }, message='登录成功')


class PasswordResetRequestView(APIView):
    """Send a one-time reset link without exposing account existence."""

    permission_classes = []

    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        if not email:
            return error_response(
                message='Email is required', code=1014,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user and user.has_usable_password():
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
            reset_url = f'{frontend_url}/reset-password?uid={uid}&token={token}'
            try:
                send_mail(
                    subject='Team management password reset',
                    message=(
                        'A password reset was requested for your account.\n\n'
                        f'Open this link to set a new password:\n{reset_url}\n\n'
                        'If you did not request this, ignore this email.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL or None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception('Password reset email delivery failed')
        return success_response(
            message='If the account exists, a password reset email has been sent.'
        )


class PasswordResetConfirmView(APIView):
    """Validate a one-time token and replace the account password."""

    permission_classes = []

    def post(self, request):
        uid = str(request.data.get('uid', ''))
        token = str(request.data.get('token', ''))
        new_password = str(request.data.get('new_password', ''))
        confirm_password = str(request.data.get('confirm_password', ''))
        if not uid or not token or not new_password:
            return error_response(
                message='Reset token and new password are required', code=1015,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if new_password != confirm_password:
            return error_response(
                message='Passwords do not match', code=1016,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is None or not default_token_generator.check_token(user, token):
            return error_response(
                message='The password reset link is invalid or expired', code=1017,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=user)
        except Exception as exc:
            messages = getattr(exc, 'messages', [str(exc)])
            return error_response(
                message='; '.join(messages), code=1018,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return success_response(message='Password reset successfully')


class ChangePasswordView(APIView):
    """
    修改密码
    - POST: 验证旧密码并设置新密码
    - 不改变 JWT 结构，修改后建议重新登录
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            name='ChangePasswordRequest',
            fields={
                'old_password': serializers.CharField(write_only=True),
                'new_password': serializers.CharField(write_only=True),
                'confirm_password': serializers.CharField(write_only=True),
            },
        ),
        responses={
            200: success_response_schema(
                'ChangePasswordResponse',
                serializers.JSONField(allow_null=True),
            ),
        },
    )
    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        # 基础校验
        if not old_password or not new_password:
            return error_response(message='请填写旧密码和新密码', code=1010)

        if new_password != confirm_password:
            return error_response(message='两次输入的新密码不一致', code=1011)

        # 验证旧密码
        user = request.user
        if not user.check_password(old_password):
            return error_response(message='旧密码错误', code=1012)

        # 新密码不能与旧密码相同
        if old_password == new_password:
            return error_response(message='新密码不能与旧密码相同', code=1013)

        # Django 密码强度验证
        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new_password, user=user)
        except Exception as e:
            return error_response(message=f'密码强度不足: {"; ".join(e.messages)}', code=1014)

        # 设置新密码
        user.set_password(new_password)
        user.save(update_fields=['password'])

        # 记录操作日志
        from apps.audit.models import OperationLog
        OperationLog.objects.create(
            operator=user,
            operation_type='update',
            module='users',
            object_type='user',
            object_id=str(user.id),
            description=f'用户 {user.email} 修改密码',
            request_method='POST',
            request_path='/api/v1/users/change-password/',
            request_ip=request.META.get('REMOTE_ADDR', ''),
        )

        return success_response(message='密码修改成功，请重新登录')


class UploadAvatarView(APIView):
    """
    头像上传
    - POST: 上传头像图片
    - 支持 jpg/jpeg/png/gif/webp
    - 最大 5MB
    - 自动保存到 avatars/ 目录
    """
    permission_classes = [IsAuthenticated]

    ALLOWED_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    @extend_schema(
        request=inline_serializer(
            name='UploadAvatarRequest',
            fields={'avatar': serializers.ImageField()},
        ),
        responses={
            200: success_response_schema(
                'UploadAvatarResponse',
                inline_serializer(
                    name='UploadAvatarData',
                    fields={'avatar': serializers.CharField()},
                ),
            ),
        },
    )
    def post(self, request):
        upload_file = request.FILES.get('avatar')
        if not upload_file:
            return error_response(message='请上传头像图片', code=1020)

        # 验证文件类型
        content_type = upload_file.content_type or ''
        if content_type not in self.ALLOWED_TYPES:
            return error_response(
                message=f'不支持的图片格式: {content_type}，请上传 JPG/PNG/GIF/WebP 格式',
                code=1021,
            )

        # 验证文件大小
        if upload_file.size > self.MAX_SIZE:
            return error_response(
                message=f'图片大小不能超过 5MB，当前: {upload_file.size / 1024 / 1024:.1f}MB',
                code=1022,
            )

        # 保存头像
        user = request.user
        # 删除旧头像（非默认头像）
        if user.avatar:
            try:
                user.avatar.delete(save=False)
            except Exception:
                pass

        user.avatar = upload_file
        user.save(update_fields=['avatar'])

        # 返回头像 URL
        avatar_url = user.avatar.url if user.avatar else ''
        return success_response(
            {'avatar': avatar_url},
            message='头像上传成功',
        )
