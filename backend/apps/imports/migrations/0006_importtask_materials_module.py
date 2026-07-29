from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('imports', '0005_importtask_team'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importtask',
            name='module',
            field=models.CharField(
                choices=[
                    ('projects', '项目'),
                    ('history_projects', '历史项目'),
                    ('members', '成员'),
                    ('competitions', '比赛'),
                    ('tasks', '任务'),
                    ('finance', '经费'),
                    ('ip_applications', '知识产权'),
                    ('materials', '资料包'),
                ],
                max_length=20,
                verbose_name='导入模块',
            ),
        ),
    ]
