import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0006_ranking_objection_adjustment'),
        ('projects', '0009_project_teams_visibility'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='contribution',
            name='source_type',
            field=models.CharField(
                choices=[
                    ('manual', '手工登记'),
                    ('task', '任务验收'),
                    ('competition', '比赛记录'),
                    ('ip', '知识产权流程'),
                    ('system', '系统证据'),
                ],
                db_index=True,
                default='manual',
                max_length=20,
                verbose_name='来源类型',
            ),
        ),
        migrations.AddField(
            model_name='contribution',
            name='source_verified',
            field=models.BooleanField(default=False, verbose_name='来源已核验'),
        ),
        migrations.CreateModel(
            name='ProjectContributionReviewer',
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
                    'is_independent',
                    models.BooleanField(
                        default=False,
                        verbose_name='可独立审核负责人申报',
                    ),
                ),
                ('priority', models.PositiveIntegerField(default=100, verbose_name='分派优先级')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                (
                    'project',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='contribution_reviewers',
                        to='projects.project',
                        verbose_name='项目',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='contribution_reviewer_assignments',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='审核人',
                    ),
                ),
            ],
            options={
                'verbose_name': '项目贡献审核人',
                'verbose_name_plural': '项目贡献审核人',
                'db_table': 'project_contribution_reviewers',
                'ordering': ['priority', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='projectcontributionreviewer',
            constraint=models.UniqueConstraint(
                fields=('project', 'user'),
                name='uniq_project_contribution_reviewer',
            ),
        ),
    ]
