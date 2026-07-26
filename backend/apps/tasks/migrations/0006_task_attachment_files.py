from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0006_filesharelink'),
        ('tasks', '0005_subtask_taskcomment_taskdependency'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='attachment_files',
            field=models.ManyToManyField(
                blank=True,
                related_name='tasks',
                to='files.fileasset',
                verbose_name='任务附件',
            ),
        ),
    ]
