from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0006_notification_email_delivery'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='resource_links',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='格式：[{"title": "资料名称", "url": "https://..."}]',
                verbose_name='资源链接',
            ),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='category',
            field=models.CharField(
                choices=[
                    ('system', '系统公告'),
                    ('project', '项目公告'),
                    ('activity', '活动公告'),
                    ('faq', '常见问题'),
                    ('template', '计划书与PPT模板'),
                    ('meeting', '会议回放'),
                    ('news', '新闻与资料'),
                    ('other', '其他'),
                ],
                default='other',
                max_length=20,
                verbose_name='类别',
            ),
        ),
    ]
