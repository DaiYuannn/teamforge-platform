from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0005_ranking_traceability'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='memberranking',
            name='rule_version',
            field=models.CharField(
                default='2026.2',
                max_length=30,
                verbose_name='排名规则版本',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='adjustment_applied_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='排名更正时间',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='adjustment_applied_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='applied_ranking_objection_adjustments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='排名更正执行人',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='adjustment_snapshot',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='排名更正快照',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='corrected_rank',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='更正后排名',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='corrected_total_score',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name='更正后总分',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='original_rank',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='更正前排名',
            ),
        ),
        migrations.AddField(
            model_name='rankingobjection',
            name='original_total_score',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name='更正前总分',
            ),
        ),
    ]
