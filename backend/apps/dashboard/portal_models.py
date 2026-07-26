"""公开门户的内容治理与站点资料。"""
from django.conf import settings
from django.db import models


class PortalSettings(models.Model):
    """公开门户单例设置。"""

    singleton_key = models.CharField(max_length=20, unique=True, default='default')
    team_name = models.CharField('团队名称', max_length=120, default='创新团队')
    tagline = models.CharField(
        '短标语',
        max_length=160,
        default='项目实践 · 赛事成长 · 成果沉淀',
    )
    summary = models.TextField(
        '团队摘要',
        default='汇聚不同专业的成员，以真实项目协作积累经验，让过程可追踪、贡献可看见、成果可延续。',
    )
    about_title = models.CharField(
        '团队介绍标题',
        max_length=160,
        default='从想法到落地，留下完整的团队记忆',
    )
    about_text = models.TextField(
        '团队介绍',
        default='这里展示团队已经完成并经确认公开的项目、赛事和知识产权成果。',
    )
    logo_url = models.CharField('标志地址', max_length=500, blank=True, default='')
    hero_image_url = models.CharField(
        '首图地址',
        max_length=500,
        blank=True,
        default='/portal/photos/lst/团队合影1.jpg',
    )
    story_image_url = models.CharField(
        '赛事图片地址',
        max_length=500,
        blank=True,
        default='/portal/photos/lst/挑战杯合影.jpg',
    )
    contact_email = models.EmailField('联系邮箱', blank=True, default='')
    join_title = models.CharField('加入我们标题', max_length=160, default='加入我们')
    join_message = models.TextField(
        '加入我们说明',
        blank=True,
        default='如果你愿意在真实项目中学习、协作和承担责任，欢迎联系我们。',
    )
    join_url = models.CharField('加入链接', max_length=500, blank=True, default='')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_portal_settings',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portal_settings'
        verbose_name = '公开门户设置'


class PortalPublication(models.Model):
    """项目、知识产权或成员的逐项公开决策。"""

    class ContentType(models.TextChoices):
        PROJECT = 'project', '项目'
        IP_APPLICATION = 'ip_application', '知识产权'
        MEMBER = 'member', '成员'

    content_type = models.CharField(
        '内容类型', max_length=30, choices=ContentType.choices
    )
    object_id = models.PositiveBigIntegerField('对象 ID')
    is_public = models.BooleanField('允许公开', default=False)
    is_featured = models.BooleanField('重点展示', default=False)
    member_consent = models.BooleanField('成员已授权', default=False)
    display_order = models.IntegerField('展示顺序', default=0)
    custom_title = models.CharField('公开标题', max_length=200, blank=True, default='')
    custom_summary = models.TextField('公开摘要', blank=True, default='')
    image_url = models.CharField('展示图片地址', max_length=500, blank=True, default='')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_portal_publications',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portal_publications'
        verbose_name = '门户公开内容'
        unique_together = [('content_type', 'object_id')]
        ordering = ['-is_featured', 'display_order', 'id']
