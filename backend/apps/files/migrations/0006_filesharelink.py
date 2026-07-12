"""
N33: 文件分享链接模型迁移
- FileShareLink: 文件分享链接（令牌访问、过期时间、最大访问次数）
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0005_file_hash_watermark'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileShareLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=64, unique=True, verbose_name='分享令牌')),
                ('expire_at', models.DateTimeField(blank=True, null=True, verbose_name='过期时间')),
                ('max_views', models.IntegerField(blank=True, null=True, verbose_name='最大访问次数')),
                ('view_count', models.IntegerField(default=0, verbose_name='访问次数')),
                ('is_active', models.BooleanField(default=True, verbose_name='有效')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='share_links', to='files.fileasset', verbose_name='文件')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='file_shares', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '文件分享链接',
                'verbose_name_plural': '文件分享链接',
                'db_table': 'file_share_links',
                'ordering': ['-created_at'],
            },
        ),
    ]
