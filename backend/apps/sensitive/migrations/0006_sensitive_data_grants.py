import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sensitive', '0005_sensitive_team_and_subject'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SensitiveDataGrant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_view', models.BooleanField(default=True, verbose_name='允许查看明文')),
                ('can_download', models.BooleanField(default=False, verbose_name='允许下载附件')),
                ('purpose', models.TextField(verbose_name='授权用途')),
                ('expires_at', models.DateTimeField(verbose_name='授权到期时间')),
                ('revoked_at', models.DateTimeField(blank=True, null=True, verbose_name='撤销时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('granted_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='issued_sensitive_data_grants', to=settings.AUTH_USER_MODEL, verbose_name='授权人')),
                ('granted_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sensitive_data_grants', to=settings.AUTH_USER_MODEL, verbose_name='被授权人')),
                ('revoked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='revoked_sensitive_data_grants', to=settings.AUTH_USER_MODEL, verbose_name='撤销人')),
                ('sensitive_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direct_grants', to='sensitive.sensitivedata', verbose_name='敏感资料')),
            ],
            options={
                'verbose_name': '敏感资料单份授权',
                'verbose_name_plural': '敏感资料单份授权',
                'db_table': 'sensitive_data_grants',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='sensitivedatagrant',
            constraint=models.UniqueConstraint(fields=('sensitive_data', 'granted_to'), name='uniq_sensitive_data_granted_user'),
        ),
        migrations.CreateModel(
            name='SensitiveGrantAccessLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('view', '查看明文'), ('download', '下载附件')], max_length=20, verbose_name='访问动作')),
                ('purpose_snapshot', models.TextField(verbose_name='用途快照')),
                ('is_success', models.BooleanField(default=True, verbose_name='是否成功')),
                ('detail', models.CharField(blank=True, default='', max_length=300, verbose_name='结果说明')),
                ('request_method', models.CharField(blank=True, default='', max_length=20, verbose_name='请求方法')),
                ('request_path', models.CharField(blank=True, default='', max_length=500, verbose_name='请求路径')),
                ('request_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='请求IP')),
                ('accessed_at', models.DateTimeField(auto_now_add=True, verbose_name='访问时间')),
                ('accessor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sensitive_grant_access_logs', to=settings.AUTH_USER_MODEL, verbose_name='访问人')),
                ('grant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='access_logs', to='sensitive.sensitivedatagrant', verbose_name='授权')),
                ('sensitive_data', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grant_access_logs', to='sensitive.sensitivedata', verbose_name='敏感资料')),
            ],
            options={
                'verbose_name': '敏感授权访问审计',
                'verbose_name_plural': '敏感授权访问审计',
                'db_table': 'sensitive_grant_access_logs',
                'ordering': ['-accessed_at'],
            },
        ),
    ]
