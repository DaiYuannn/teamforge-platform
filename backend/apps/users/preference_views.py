"""
用户个人化偏好设置视图
GET /api/v1/users/preference/   获取当前用户偏好设置（不存在则返回默认值）
PUT /api/v1/users/preference/   更新偏好设置（不存在则自动创建）
"""
import re
from collections.abc import Mapping

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from .models import UserPreference


# 偏好设置默认值（与模型字段 default 保持一致）
_DEFAULT_PREFERENCE = {
    'dashboard_layout': {},
    'theme_color': UserPreference.DEFAULT_THEME,
    'primary_color': UserPreference.DEFAULT_PRIMARY_COLOR,
    'default_landing': 'dashboard',
    'sidebar_collapsed': False,
    'notification_sound': True,
    'items_per_page': 20,
    'default_scope': 'mine',
    'sidebar_order': [],
    'favorite_routes': [],
    'saved_filters': {},
    'notification_preferences': {},
}

# 允许更新的字段白名单
_ALLOWED_FIELDS = {
    'dashboard_layout',
    'theme_color',
    'primary_color',
    'default_landing',
    'sidebar_collapsed',
    'notification_sound',
    'items_per_page',
    'default_scope',
    'sidebar_order',
    'favorite_routes',
    'saved_filters',
    'notification_preferences',
}

# 各字段的合法取值校验
_VALID_CHOICES = {
    'theme_color': set(UserPreference.THEME_TO_PRIMARY_COLOR),
    'default_landing': {'dashboard', 'projects', 'tasks', 'notifications'},
    'items_per_page': {10, 20, 50},
    'default_scope': {'mine', 'team'},
}

_BOOLEAN_FIELDS = {'sidebar_collapsed', 'notification_sound'}
_NOTIFICATION_FIELDS = {'categories', 'channels', 'quiet_hours', 'digest'}
_QUIET_HOUR_FIELDS = {'enabled', 'start', 'end'}
_DIGEST_CHOICES = {'instant', 'daily', 'weekly'}
_CLOCK_PATTERN = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d$')


def _unique_string_list(value):
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
        and len(value) == len(set(value))
    )


def _validate_boolean_mapping(field, value):
    if not isinstance(value, dict):
        return f'notification_preferences.{field} 必须为对象类型'
    if not all(
        isinstance(key, str)
        and bool(key.strip())
        and type(enabled) is bool
        for key, enabled in value.items()
    ):
        return f'notification_preferences.{field} 必须是字符串到布尔值的映射'
    return None


def _validate_notification_preferences(value):
    if not isinstance(value, dict):
        return 'notification_preferences 必须为对象类型'

    unknown = [key for key in value if key not in _NOTIFICATION_FIELDS]
    if unknown:
        return f'notification_preferences 包含未知字段：{", ".join(map(str, unknown))}'

    for field in ('categories', 'channels'):
        if field in value:
            error = _validate_boolean_mapping(field, value[field])
            if error:
                return error

    if 'quiet_hours' in value:
        quiet_hours = value['quiet_hours']
        if not isinstance(quiet_hours, dict):
            return 'notification_preferences.quiet_hours 必须为对象类型'
        unknown_quiet_fields = [
            key for key in quiet_hours if key not in _QUIET_HOUR_FIELDS
        ]
        if unknown_quiet_fields:
            return (
                'notification_preferences.quiet_hours 包含未知字段：'
                f'{", ".join(map(str, unknown_quiet_fields))}'
            )
        if (
            'enabled' in quiet_hours
            and type(quiet_hours['enabled']) is not bool
        ):
            return 'notification_preferences.quiet_hours.enabled 必须为布尔值'
        for field in ('start', 'end'):
            if field in quiet_hours and (
                not isinstance(quiet_hours[field], str)
                or not _CLOCK_PATTERN.fullmatch(quiet_hours[field])
            ):
                return (
                    f'notification_preferences.quiet_hours.{field} '
                    '必须为 HH:MM 格式的有效时间'
                )

    if 'digest' in value and (
        not isinstance(value['digest'], str)
        or value['digest'] not in _DIGEST_CHOICES
    ):
        return 'notification_preferences.digest 可选值为 instant、daily、weekly'
    return None


class UserPreferenceView(APIView):
    """
    用户个人化偏好设置视图
    - GET: 返回当前用户偏好设置（不存在则返回默认值）
    - PUT: 更新偏好设置（不存在则自动创建）
    - 权限: IsAuthenticated
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取当前用户偏好设置"""
        user = request.user
        try:
            pref = UserPreference.objects.get(user=user)
        except UserPreference.DoesNotExist:
            # 不存在记录时返回默认值，不自动创建
            data = dict(_DEFAULT_PREFERENCE)
            data['user_id'] = user.id
            return success_response(data)

        return success_response(self._serialize(pref))

    def put(self, request):
        """更新当前用户偏好设置"""
        user = request.user
        data = request.data

        if not isinstance(data, Mapping):
            return error_response(message='偏好设置必须为对象类型', code=1001)

        unknown_fields = [field for field in data.keys() if field not in _ALLOWED_FIELDS]
        if unknown_fields:
            return error_response(
                message=f'包含未知字段：{", ".join(map(str, unknown_fields))}',
                code=1001,
            )

        update_data = {
            field: data[field]
            for field in _ALLOWED_FIELDS
            if field in data
        }
        if not update_data:
            return error_response(message='请至少提交一个偏好字段', code=1001)

        for field in _BOOLEAN_FIELDS:
            if field in update_data and type(update_data[field]) is not bool:
                return error_response(message=f'字段 {field} 必须为布尔值', code=1001)

        # 先校验用户原始枚举值的类型，避免列表或对象触发集合查找异常。
        for field, valid_values in _VALID_CHOICES.items():
            if field not in update_data:
                continue
            value = update_data[field]
            expected_type = int if field == 'items_per_page' else str
            if type(value) is not expected_type or value not in valid_values:
                return error_response(
                    message=f'字段 {field} 的值不合法，可选值：{sorted(valid_values)}',
                    code=1001,
                )

        has_primary_color = 'primary_color' in update_data
        primary_color = update_data.get('primary_color')
        if has_primary_color:
            normalized_color = UserPreference.normalize_primary_color(primary_color)
            if normalized_color is None:
                return error_response(
                    message='字段 primary_color 必须是完整的六位十六进制颜色，例如 #176b73',
                    code=1001,
                )
            update_data['primary_color'] = normalized_color
            theme_from_primary = UserPreference.theme_for_primary_color(normalized_color)
            if theme_from_primary is not None:
                update_data['theme_color'] = theme_from_primary

        # 旧客户端仍可只提交 theme_color；转换为同一套主色字段持久化。
        if 'theme_color' in update_data and not has_primary_color:
            update_data['primary_color'] = UserPreference.primary_color_for_theme(
                update_data['theme_color']
            )

        # 校验 dashboard_layout 必须为 dict
        if 'dashboard_layout' in update_data:
            if not isinstance(update_data['dashboard_layout'], dict):
                return error_response(
                    message='dashboard_layout 必须为对象类型',
                    code=1001,
                )

        for field in ('sidebar_order', 'favorite_routes'):
            if field in update_data and not _unique_string_list(update_data[field]):
                return error_response(
                    message=f'{field} 必须为不含重复项的非空字符串数组',
                    code=1001,
                )

        if 'saved_filters' in update_data:
            saved_filters = update_data['saved_filters']
            if not isinstance(saved_filters, dict) or not all(
                isinstance(module, str)
                and bool(module.strip())
                and isinstance(filters, dict)
                for module, filters in saved_filters.items()
            ):
                return error_response(
                    message='saved_filters 必须是模块名称到筛选对象的映射',
                    code=1001,
                )

        if 'notification_preferences' in update_data:
            validation_error = _validate_notification_preferences(
                update_data['notification_preferences']
            )
            if validation_error:
                return error_response(message=validation_error, code=1001)

        # 使用 get_or_create：不存在则创建，存在则更新
        pref, created = UserPreference.objects.get_or_create(user=user)
        for field, value in update_data.items():
            setattr(pref, field, value)
        pref.save()

        message = '偏好设置已创建' if created else '偏好设置已更新'
        return success_response(self._serialize(pref), message=message)

    def patch(self, request):
        """PATCH 与原有部分更新语义一致。"""
        return self.put(request)

    @staticmethod
    def _serialize(pref):
        """序列化偏好设置对象为字典"""
        return {
            'user_id': pref.user_id,
            'dashboard_layout': pref.dashboard_layout or {},
            'theme_color': (
                pref.theme_color
                if pref.theme_color in UserPreference.THEME_TO_PRIMARY_COLOR
                else UserPreference.DEFAULT_THEME
            ),
            'primary_color': pref.safe_primary_color,
            'default_landing': pref.default_landing,
            'sidebar_collapsed': pref.sidebar_collapsed,
            'notification_sound': pref.notification_sound,
            'items_per_page': pref.items_per_page,
            'default_scope': pref.default_scope,
            'sidebar_order': pref.sidebar_order or [],
            'favorite_routes': pref.favorite_routes or [],
            'saved_filters': pref.saved_filters or {},
            'notification_preferences': pref.notification_preferences or {},
        }
