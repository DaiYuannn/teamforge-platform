"""
用户序列化器
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field

from .models import User, UserPreference, UserLifecycleEvent


def _serialize_preferences(user):
    try:
        preference = user.preference
    except UserPreference.DoesNotExist:
        return {
            'dashboard_layout': {},
            'theme_color': UserPreference.DEFAULT_THEME,
            'primary_color': UserPreference.DEFAULT_PRIMARY_COLOR,
            'theme_mode': UserPreference.DEFAULT_THEME_MODE,
            'schedule_start': UserPreference.DEFAULT_SCHEDULE_START,
            'schedule_end': UserPreference.DEFAULT_SCHEDULE_END,
            'default_landing': 'dashboard',
            'sidebar_collapsed': False,
            'notification_sound': True,
            'language': UserPreference.DEFAULT_LANGUAGE,
            'items_per_page': 20,
            'default_scope': 'mine',
            'sidebar_order': [],
            'favorite_routes': [],
            'saved_filters': {},
            'notification_preferences': {},
        }
    return {
        'dashboard_layout': preference.dashboard_layout or {},
        'theme_color': (
            preference.theme_color
            if preference.theme_color in UserPreference.THEME_TO_PRIMARY_COLOR
            else UserPreference.DEFAULT_THEME
        ),
        'primary_color': preference.safe_primary_color,
        'theme_mode': preference.theme_mode,
        'schedule_start': preference.schedule_start,
        'schedule_end': preference.schedule_end,
        'default_landing': preference.default_landing,
        'sidebar_collapsed': preference.sidebar_collapsed,
        'notification_sound': preference.notification_sound,
        'language': preference.language,
        'items_per_page': preference.items_per_page,
        'default_scope': preference.default_scope,
        'sidebar_order': preference.sidebar_order or [],
        'favorite_routes': preference.favorite_routes or [],
        'saved_filters': preference.saved_filters or {},
        'notification_preferences': preference.notification_preferences or {},
    }


def _global_permission_codes(user):
    """Return custom permission codes granted without a project scope."""
    codes = set()
    assignments = user.role_assignments.filter(
        project__isnull=True,
    ).select_related('role')
    for assignment in assignments:
        codes.update(assignment.role.permissions or [])
    return sorted(codes)


class UserPreferencesPayloadSerializer(serializers.Serializer):
    dashboard_layout = serializers.JSONField()
    theme_color = serializers.CharField()
    primary_color = serializers.CharField()
    theme_mode = serializers.ChoiceField(choices=UserPreference.ThemeMode.choices)
    schedule_start = serializers.RegexField(UserPreference.SCHEDULE_TIME_PATTERN)
    schedule_end = serializers.RegexField(UserPreference.SCHEDULE_TIME_PATTERN)
    default_landing = serializers.CharField()
    sidebar_collapsed = serializers.BooleanField()
    notification_sound = serializers.BooleanField()
    language = serializers.ChoiceField(choices=['zh-CN', 'en'])
    items_per_page = serializers.IntegerField()
    default_scope = serializers.CharField()
    sidebar_order = serializers.ListField(child=serializers.CharField())
    favorite_routes = serializers.ListField(child=serializers.CharField())
    saved_filters = serializers.JSONField()
    notification_preferences = serializers.JSONField()


class UserLifecycleEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    handover_to_name = serializers.CharField(source='handover_to.name', read_only=True, default='')

    class Meta:
        model = UserLifecycleEvent
        fields = (
            'id', 'event_type', 'event_type_display', 'from_status', 'to_status',
            'from_role', 'to_role', 'reason', 'handover_to', 'handover_to_name',
            'handover_notes', 'operator', 'operator_name', 'created_at',
        )
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """用户完整序列化器（详情/管理用）"""
    preferences = serializers.SerializerMethodField()
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at',
            'exit_reason', 'handover_to', 'handover_notes',
            'is_active', 'is_staff', 'date_joined', 'last_login', 'preferences',
            'permission_codes',
        )
        read_only_fields = ('id', 'date_joined', 'last_login')

    @extend_schema_field(UserPreferencesPayloadSerializer)
    def get_preferences(self, obj):
        return _serialize_preferences(obj)

    def get_permission_codes(self, obj):
        return _global_permission_codes(obj)


class UserListSerializer(serializers.ModelSerializer):
    """用户列表精简序列化器"""

    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at',
            'handover_to', 'is_active',
        )
        read_only_fields = fields


class ExternalCollaboratorUserSerializer(serializers.ModelSerializer):
    """外部协作者在已分配项目中可见的最小成员身份信息。"""

    global_role_display = serializers.CharField(
        source='get_global_role_display',
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            'id', 'name', 'avatar', 'global_role', 'global_role_display',
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
            'global_role', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at',
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
            'global_role', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at',
            'exit_reason', 'handover_to', 'handover_notes',
            'is_active', 'is_staff',
        )
        read_only_fields = ('id',)


class MyProfileSerializer(serializers.ModelSerializer):
    """当前用户个人信息序列化器（用户自己编辑个人信息）"""
    preferences = serializers.SerializerMethodField()
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'phone', 'avatar',
            'global_role', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at',
            'is_active', 'date_joined', 'last_login', 'preferences',
            'permission_codes',
        )
        read_only_fields = (
            'id', 'username', 'email', 'global_role',
            'membership_status', 'team_joined_at', 'team_left_at',
            'is_active', 'date_joined', 'last_login',
        )

    @extend_schema_field(UserPreferencesPayloadSerializer)
    def get_preferences(self, obj):
        return _serialize_preferences(obj)

    def get_permission_codes(self, obj):
        return _global_permission_codes(obj)


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)
