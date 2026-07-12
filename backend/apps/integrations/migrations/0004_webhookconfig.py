# Generated for WebhookConfig model (P09)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0003_remove_feishu_qqbot_providers'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('url', models.URLField(verbose_name='Webhook 地址')),
                ('secret', models.CharField(blank=True, default='', max_length=200, verbose_name='签名密钥')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('events', models.JSONField(blank=True, default=list, verbose_name='订阅事件')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': 'Webhook配置',
                'verbose_name_plural': 'Webhook配置',
                'db_table': 'webhook_configs',
                'ordering': ['-created_at'],
            },
        ),
    ]
