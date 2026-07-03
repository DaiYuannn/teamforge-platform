"""
审计日志模型（架构预留）
包含 OperationLog（操作日志）
记录用户的关键操作，用于审计追踪
"""
from django.db import models
from django.conf import settings


class OperationLog(models.Model):
    """
    操作日志模型（架构预留）
    记录用户的关键操作（增删改），用于审计追踪
    """

    class OperationType(models.TextChoices):
        """操作类型"""
        CREATE = 'create', '创建'
        UPDATE = 'update', '更新'
        DELETE = 'delete', '删除'
        LOGIN = 'login', '登录'
        LOGOUT = 'logout', '登出'
        EXPORT = 'export', '导出'
        IMPORT = 'import', '导入'
        UPLOAD = 'upload', '上传'
        DOWNLOAD = 'download', '下载'
        APPROVE = 'approve', '审批'
        REJECT = 'reject', '驳回'
        REVIEW = 'review', '审核'
        VIEW_SENSITIVE = 'view_sensitive', '查看敏感'
        OTHER = 'other', '其他'

    # 操作人
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='operation_logs',
        verbose_name='操作人',
        null=True, blank=True,
    )
    # 操作类型
    operation_type = models.CharField(
        '操作类型',
        max_length=20,
        choices=OperationType.choices,
        default=OperationType.OTHER,
    )
    # 操作模块
    module = models.CharField('操作模块', max_length=50, blank=True, default='')
    # 操作对象类型
    object_type = models.CharField('对象类型', max_length=100, blank=True, default='')
    # 操作对象ID
    object_id = models.CharField('对象ID', max_length=50, blank=True, default='')
    # 操作描述
    description = models.TextField('操作描述', blank=True, default='')
    # 请求方法
    request_method = models.CharField('请求方法', max_length=10, blank=True, default='')
    # 请求路径
    request_path = models.CharField('请求路径', max_length=500, blank=True, default='')
    # 请求IP
    request_ip = models.GenericIPAddressField('请求IP', null=True, blank=True)
    # User-Agent（客户端信息）
    user_agent = models.CharField('User-Agent', max_length=500, blank=True, default='')
    # 请求参数（JSON格式）
    request_data = models.JSONField('请求参数', null=True, blank=True)
    # 响应状态码
    response_status = models.IntegerField('响应状态码', null=True, blank=True)
    # 是否成功
    is_success = models.BooleanField('是否成功', default=True)
    # 错误信息
    error_message = models.TextField('错误信息', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'operation_logs'
        verbose_name = '操作日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.operator} - {self.get_operation_type_display()} - {self.module}({self.created_at})'
