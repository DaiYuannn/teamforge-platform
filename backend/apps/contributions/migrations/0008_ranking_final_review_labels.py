from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0007_reviewer_routing_and_sources'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rankingobjection',
            name='teacher_confirmer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ranking_objection_teacher_confirms',
                to='users.user',
                verbose_name='最终复核人',
            ),
        ),
        migrations.AlterField(
            model_name='rankingobjection',
            name='teacher_confirmed_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='最终复核时间',
            ),
        ),
        migrations.AlterField(
            model_name='rankingobjection',
            name='teacher_opinion',
            field=models.TextField(
                blank=True,
                default='',
                verbose_name='最终复核意见',
            ),
        ),
    ]
