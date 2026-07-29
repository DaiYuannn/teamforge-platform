import django.db.models.deletion
import django
from django.db import migrations, models


CHECK_CONDITION_ARG = 'condition' if django.VERSION >= (5, 1) else 'check'


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0007_activity_organization_and_types'),
        ('competitions', '0005_competitionevent_competition_entry_name_and_more'),
        ('files', '0007_fileasset_deleted_at_fileasset_deleted_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileasset',
            name='competition_entry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='scoped_files', to='competitions.competition', verbose_name='指定可见参赛条目'),
        ),
        migrations.AddField(
            model_name='fileasset',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='scoped_files', to='common.team', verbose_name='指定可见团队'),
        ),
        migrations.AddConstraint(
            model_name='fileasset',
            constraint=models.CheckConstraint(
                name='file_scope_team_or_competition',
                **{
                    CHECK_CONDITION_ARG: (
                        models.Q(team__isnull=True)
                        | models.Q(competition_entry__isnull=True)
                    ),
                },
            ),
        ),
    ]
