import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_team_hierarchy_and_co_lead'),
        ('imports', '0004_alter_importtask_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='importtask',
            name='team',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='import_tasks',
                to='common.team',
                verbose_name='所属团队',
            ),
        ),
    ]
