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
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .models import User
from .serializers import (
    UserSerializer, UserListSerializer, UserCreateSerializer,
    UserUpdateSerializer, MyProfileSerializer, LoginSerializer,
)
from .permissions import IsUserManager, IsSelfOrAdmin
from .login_security_services import (
    get_client_ip, get_user_agent, is_ip_blocked, record_login_attempt,
)


class UserViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    用户管理 ViewSet
    - list/retrieve: 老师/管理员可查看
    - create/update/destroy: 仅管理员
    """
    queryset = User.objects.all().order_by('-date_joined')

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

    filterset_fields = ['global_role', 'is_student', 'is_active', 'grade', 'major']
    search_fields = ['username', 'email', 'name', 'phone']
    ordering_fields = ['date_joined', 'name', 'email']

    def create(self, request, *args, **kwargs):
        """创建用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(
            UserSerializer(user).data,
            message='用户创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新用户"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(UserSerializer(user).data, message='用户更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除用户"""
        instance = self.get_object()
        # 不允许删除自己
        if instance.id == request.user.id:
            return error_response(message='不能删除当前登录用户', code=1007)
        instance.delete()
        return success_response(message='用户删除成功')


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

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

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

        if not user.is_active:
            record_login_attempt(
                email=email, ip_address=ip_address, user_agent=user_agent,
                is_success=False, failure_reason='账号已禁用',
            )
            return error_response(message='账号已被禁用，请联系管理员', code=1002,
                                  http_status=status.HTTP_403_FORBIDDEN)

        # 登录成功，记录成功尝试
        record_login_attempt(
            email=email, ip_address=ip_address, user_agent=user_agent,
            is_success=True, failure_reason='',
        )

        # 生成 JWT token
        refresh = RefreshToken.for_user(user)

        return success_response({
            'token': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'user': UserSerializer(user).data,
        }, message='登录成功')


class ChangePasswordView(APIView):
    """
    修改密码
    - POST: 验证旧密码并设置新密码
    - 不改变 JWT 结构，修改后建议重新登录
    """
    permission_classes = [IsAuthenticated]

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
