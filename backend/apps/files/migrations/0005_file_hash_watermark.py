"""
N31/N32: 文件哈希 + 水印文字字段
- file_hash: SHA-256 文件哈希（用于查重）
- watermark_text: 水印文字（可选，下载水印版本时使用）
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0004_filetag_filetagrelation'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileasset',
            name='file_hash',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='文件哈希'),
        ),
        migrations.AddField(
            model_name='fileasset',
            name='watermark_text',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='水印文字'),
        ),
    ]
