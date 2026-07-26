from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_notification_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='email_attempted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='邮件尝试时间'),
        ),
        migrations.AddField(
            model_name='notification',
            name='email_delivery_error',
            field=models.TextField(blank=True, default='', verbose_name='邮件投递错误'),
        ),
        migrations.AddField(
            model_name='notification',
            name='email_delivery_status',
            field=models.CharField(
                choices=[
                    ('not_requested', '未请求'),
                    ('queued', '等待摘要'),
                    ('sent', '已发送'),
                    ('failed', '发送失败'),
                    ('suppressed', '已按偏好关闭'),
                ],
                db_index=True,
                default='not_requested',
                max_length=20,
                verbose_name='邮件投递状态',
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='email_digest_frequency',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='邮件摘要频率'),
        ),
        migrations.AddField(
            model_name='notification',
            name='email_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='邮件发送时间'),
        ),
    ]
