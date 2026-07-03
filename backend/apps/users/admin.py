"""users 应用的 Django Admin 配置"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理后台"""
    list_display = ('id', 'username', 'email', 'name', 'global_role', 'is_student', 'is_active', 'date_joined')
    list_filter = ('global_role', 'is_student', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'name', 'phone')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('name', 'email', 'phone', 'avatar', 'global_role',
                                  'is_student', 'grade', 'major')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'name', 'password1', 'password2', 'global_role'),
        }),
    )
