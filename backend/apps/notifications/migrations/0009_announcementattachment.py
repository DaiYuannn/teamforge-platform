import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0008_announcement_audience'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnouncementAttachment',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'file',
                    models.FileField(
                        upload_to='announcements/%Y%m/',
                        verbose_name='附件文件',
                    ),
                ),
                ('name', models.CharField(max_length=255, verbose_name='文件名称')),
                ('size', models.BigIntegerField(default=0, verbose_name='文件大小')),
                (
                    'content_type',
                    models.CharField(
                        blank=True,
                        default='',
                        max_length=100,
                        verbose_name='内容类型',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='上传时间')),
                (
                    'announcement',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='attachments',
                        to='notifications.announcement',
                        verbose_name='所属公告',
                    ),
                ),
                (
                    'uploaded_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='uploaded_announcement_attachments',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='上传人',
                    ),
                ),
            ],
            options={
                'verbose_name': '公告附件',
                'verbose_name_plural': '公告附件',
                'db_table': 'announcement_attachments',
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
