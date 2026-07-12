# Generated for Project.archived_at field (P13)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_add_project_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='归档时间'),
        ),
    ]
