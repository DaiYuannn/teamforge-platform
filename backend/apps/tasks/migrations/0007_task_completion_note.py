from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_task_attachment_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='completion_note',
            field=models.TextField(blank=True, default='', verbose_name='完成说明'),
        ),
    ]
