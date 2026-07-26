from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def initialize_snapshots(apps, schema_editor):
    MemberRanking = apps.get_model('contributions', 'MemberRanking')
    for ranking in MemberRanking.objects.all().iterator():
        ranking.rule_snapshot = {
            'version': 'legacy',
            'description': '升级前排名，保留原总分和统计字段',
        }
        ranking.score_snapshot = {
            'legacy': True,
            'total_score': str(ranking.total_score),
            'task_completed_count': ranking.task_completed_count,
            'competition_count': ranking.competition_count,
            'ip_contribution_count': ranking.ip_contribution_count,
        }
        ranking.generated_at = ranking.created_at
        if ranking.status == 'confirmed':
            ranking.confirmed_at = ranking.updated_at
        ranking.save(
            update_fields=[
                'rule_snapshot', 'score_snapshot',
                'generated_at', 'confirmed_at',
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0004_alter_memberranking_unique_together_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='memberranking',
            name='confirmed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='排名确认时间'),
        ),
        migrations.AddField(
            model_name='memberranking',
            name='confirmed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='confirmed_rankings', to=settings.AUTH_USER_MODEL, verbose_name='排名确认人'),
        ),
        migrations.AddField(
            model_name='memberranking',
            name='generated_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='排名生成时间'),
        ),
        migrations.AddField(
            model_name='memberranking',
            name='rule_snapshot',
            field=models.JSONField(blank=True, default=dict, verbose_name='排名规则快照'),
        ),
        migrations.AddField(
            model_name='memberranking',
            name='rule_version',
            field=models.CharField(default='2026.1', max_length=30, verbose_name='排名规则版本'),
        ),
        migrations.AddField(
            model_name='memberranking',
            name='score_snapshot',
            field=models.JSONField(blank=True, default=dict, verbose_name='计分证据快照'),
        ),
        migrations.RunPython(initialize_snapshots, migrations.RunPython.noop),
    ]
