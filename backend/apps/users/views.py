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
    """
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # 通过 email 查找用户并验证密码
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response(message='邮箱或密码错误', code=1001,
                                  http_status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return error_response(message='邮箱或密码错误', code=1001,
                                  http_status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return error_response(message='账号已被禁用，请联系管理员', code=1002,
                                  http_status=status.HTTP_403_FORBIDDEN)

        # 生成 JWT token
        refresh = RefreshToken.for_user(user)

        return success_response({
            'token': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'user': UserSerializer(user).data,
        }, message='登录成功')
