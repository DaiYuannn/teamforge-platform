"""
用户序列化器
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """用户完整序列化器（详情/管理用）"""

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'is_student', 'grade', 'major',
            'is_active', 'is_staff', 'date_joined', 'last_login',
        )
        read_only_fields = ('id', 'date_joined', 'last_login')


class UserListSerializer(serializers.ModelSerializer):
    """用户列表精简序列化器"""

    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'grade', 'major',
            'is_active',
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'is_student', 'grade', 'major',
            'password', 'password_confirm',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        """校验两次密码一致"""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': '两次输入的密码不一致'})
        attrs.pop('password_confirm', None)
        return attrs

    def create(self, validated_data):
        """创建用户"""
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户更新序列化器（管理员编辑用户）"""

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'is_student', 'grade', 'major',
            'is_active', 'is_staff',
        )
        read_only_fields = ('id',)


class MyProfileSerializer(serializers.ModelSerializer):
    """当前用户个人信息序列化器（用户自己编辑个人信息）"""

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'is_student', 'grade', 'major',
        )
        read_only_fields = ('id', 'username', 'email', 'global_role')


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
