"""
用户个人化偏好设置视图
GET /api/v1/users/preference/   获取当前用户偏好设置（不存在则返回默认值）
PUT /api/v1/users/preference/   更新偏好设置（不存在则自动创建）
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from .models import UserPreference


# 偏好设置默认值（与模型字段 default 保持一致）
_DEFAULT_PREFERENCE = {
    'dashboard_layout': {},
    'theme_color': 'blue',
    'default_landing': 'dashboard',
    'sidebar_collapsed': False,
    'notification_sound': True,
    'items_per_page': 20,
}

# 允许更新的字段白名单
_ALLOWED_FIELDS = {
    'dashboard_layout',
    'theme_color',
    'default_landing',
    'sidebar_collapsed',
    'notification_sound',
    'items_per_page',
}

# 各字段的合法取值校验
_VALID_CHOICES = {
    'theme_color': {'blue', 'green', 'purple', 'orange'},
    'default_landing': {'dashboard', 'projects', 'tasks', 'notifications'},
    'items_per_page': {10, 20, 50},
}


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

        # 过滤出允许更新的字段
        update_data = {}
        for field in _ALLOWED_FIELDS:
            if field in data:
                update_data[field] = data[field]

        # 校验枚举字段的合法取值
        for field, valid_values in _VALID_CHOICES.items():
            if field in update_data and update_data[field] not in valid_values:
                return error_response(
                    message=f'字段 {field} 的值不合法，可选值：{valid_values}',
                    code=1001,
                )

        # 校验 dashboard_layout 必须为 dict
        if 'dashboard_layout' in update_data:
            if not isinstance(update_data['dashboard_layout'], dict):
                return error_response(
                    message='dashboard_layout 必须为对象类型',
                    code=1001,
                )

        # 使用 get_or_create：不存在则创建，存在则更新
        pref, created = UserPreference.objects.get_or_create(user=user)
        for field, value in update_data.items():
            setattr(pref, field, value)
        pref.save()

        message = '偏好设置已创建' if created else '偏好设置已更新'
        return success_response(self._serialize(pref), message=message)

    @staticmethod
    def _serialize(pref):
        """序列化偏好设置对象为字典"""
        return {
            'user_id': pref.user_id,
            'dashboard_layout': pref.dashboard_layout or {},
            'theme_color': pref.theme_color,
            'default_landing': pref.default_landing,
            'sidebar_collapsed': pref.sidebar_collapsed,
            'notification_sound': pref.notification_sound,
            'items_per_page': pref.items_per_page,
        }
