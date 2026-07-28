import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_primary_project_links(apps, schema_editor):
    Application = apps.get_model('intellectual_property', 'IntellectualPropertyApplication')
    ProjectLink = apps.get_model('intellectual_property', 'IPApplicationProjectLink')
    links = [
        ProjectLink(
            application_id=application.id,
            project_id=application.related_project_id,
            relation_type='primary',
        )
        for application in Application.objects.exclude(related_project_id=None).iterator()
    ]
    ProjectLink.objects.bulk_create(links, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('intellectual_property', '0002_initial'),
        ('projects', '0009_project_teams_visibility'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='intellectualpropertyapplication',
            name='status_note',
            field=models.TextField(blank=True, default='', verbose_name='状态说明'),
        ),
        migrations.CreateModel(
            name='IPApplicationProjectLink',
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
                    'relation_type',
                    models.CharField(
                        choices=[
                            ('primary', '主项目'),
                            ('source', '成果来源'),
                            ('used_by', '成果复用'),
                        ],
                        default='used_by',
                        max_length=20,
                        verbose_name='关联类型',
                    ),
                ),
                ('note', models.TextField(blank=True, default='', verbose_name='关联说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='关联时间')),
                (
                    'application',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='project_links',
                        to='intellectual_property.intellectualpropertyapplication',
                        verbose_name='知识产权申请',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='ip_application_links',
                        to='projects.project',
                        verbose_name='关联项目',
                    ),
                ),
            ],
            options={
                'verbose_name': '知识产权关联项目',
                'verbose_name_plural': '知识产权关联项目',
                'db_table': 'ip_application_project_links',
            },
        ),
        migrations.AddConstraint(
            model_name='ipapplicationprojectlink',
            constraint=models.UniqueConstraint(
                fields=('application', 'project'),
                name='uniq_ip_application_project',
            ),
        ),
        migrations.AddConstraint(
            model_name='ipapplicationprojectlink',
            constraint=models.UniqueConstraint(
                condition=models.Q(('relation_type', 'primary')),
                fields=('application',),
                name='uniq_primary_project_per_ip_application',
            ),
        ),
        migrations.AddField(
            model_name='intellectualpropertyapplication',
            name='related_projects',
            field=models.ManyToManyField(
                blank=True,
                related_name='linked_ip_applications',
                through='intellectual_property.IPApplicationProjectLink',
                to='projects.project',
                verbose_name='关联项目',
            ),
        ),
        migrations.CreateModel(
            name='IPApplicationCandidate',
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
                    'legal_role',
                    models.CharField(
                        choices=[
                            ('inventor', '发明人'),
                            ('author', '著作权人/作者'),
                            ('applicant', '申请人'),
                            ('other', '其他申报身份'),
                        ],
                        default='inventor',
                        max_length=20,
                        verbose_name='申报身份',
                    ),
                ),
                ('planned_order', models.PositiveIntegerField(default=1, verbose_name='拟署名顺序')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('proposed', '拟申报'),
                            ('identity_pending', '待身份核验'),
                            ('confirmed', '已确认'),
                            ('submitted', '已正式提交'),
                            ('withdrawn', '已撤出'),
                        ],
                        db_index=True,
                        default='proposed',
                        max_length=30,
                        verbose_name='名单状态',
                    ),
                ),
                (
                    'identity_check_status',
                    models.CharField(
                        choices=[
                            ('pending', '待核验'),
                            ('matched', '姓名证件一致'),
                            ('mismatched', '姓名证件不一致'),
                            ('not_required', '无需核验'),
                        ],
                        default='pending',
                        max_length=20,
                        verbose_name='身份核验状态',
                    ),
                ),
                ('checked_at', models.DateTimeField(blank=True, null=True, verbose_name='核验时间')),
                ('note', models.TextField(blank=True, default='', verbose_name='说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                (
                    'application',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='candidates',
                        to='intellectual_property.intellectualpropertyapplication',
                        verbose_name='知识产权申请',
                    ),
                ),
                (
                    'checked_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='checked_ip_candidates',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='核验人',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='ip_candidate_records',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='拟申报成员',
                    ),
                ),
            ],
            options={
                'verbose_name': '知识产权拟申报名单',
                'verbose_name_plural': '知识产权拟申报名单',
                'db_table': 'ip_application_candidates',
                'ordering': ['planned_order', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='ipapplicationcandidate',
            constraint=models.UniqueConstraint(
                fields=('application', 'user', 'legal_role'),
                name='uniq_ip_candidate_legal_role',
            ),
        ),
        migrations.RunPython(backfill_primary_project_links, migrations.RunPython.noop),
    ]
