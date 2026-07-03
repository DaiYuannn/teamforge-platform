"""
数据导入模型
导入流程: preview(上传+解析+字段映射+返回预览) -> confirm(事务写入) -> rollback(根据快照回滚)
"""
from django.db import models
from django.conf import settings


class ImportTask(models.Model):
    """
    导入任务模型
    记录每次数据导入的任务信息，支持预览、确认、回滚
    """

    class Module(models.TextChoices):
        """导入模块"""
        PROJECTS = 'projects', '项目'
        MEMBERS = 'members', '成员'
        COMPETITIONS = 'competitions', '比赛'
        TASKS = 'tasks', '任务'
        FINANCE = 'finance', '经费'

    class Status(models.TextChoices):
        """导入状态"""
        PENDING = 'pending', '待处理'
        PREVIEWING = 'previewing', '预览中'
        PREVIEWED = 'previewed', '已预览'
        CONFIRMING = 'confirming', '确认中'
        CONFIRMED = 'confirmed', '已确认'
        FAILED = 'failed', '失败'
        ROLLED_BACK = 'rolled_back', '已回滚'

    # 导入模块
    module = models.CharField(
        '导入模块',
        max_length=20,
        choices=Module.choices,
    )
    # 文件路径
    file_path = models.CharField('文件路径', max_length=500)
    # 导入状态
    status = models.CharField(
        '导入状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # 字段映射（JSON格式：源列名 -> 目标字段名）
    field_mapping = models.JSONField('字段映射', default=dict, blank=True)
    # 预览数据（JSON格式：前N行预览数据）
    preview_data = models.JSONField('预览数据', null=True, blank=True)
    # 写入快照（JSON格式：用于回滚的已写入数据ID列表）
    snapshot = models.JSONField('写入快照', default=list, blank=True)
    # 总行数
    total_rows = models.IntegerField('总行数', default=0)
    # 有效行数
    valid_rows = models.IntegerField('有效行数', default=0)
    # 错误行数
    error_rows = models.IntegerField('错误行数', default=0)
    # 错误详情（JSON格式：行号 -> 错误信息）
    error_details = models.JSONField('错误详情', default=dict, blank=True)
    # 创建人
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='import_tasks',
        verbose_name='创建人',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'import_tasks'
        verbose_name = '导入任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_module_display()}导入任务({self.id}) - {self.get_status_display()}'
