import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_team_hierarchy_and_co_lead'),
        ('projects', '0008_projectmember_exit_reason_projectmember_exited_at_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='teams',
            field=models.ManyToManyField(
                blank=True,
                related_name='projects',
                to='common.team',
                verbose_name='关联团队',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='visibility',
            field=models.CharField(
                choices=[
                    ('project', '仅项目成员'),
                    ('teams', '关联小组'),
                    ('organization', '全团队'),
                ],
                db_index=True,
                default='organization',
                max_length=20,
                verbose_name='可见范围',
            ),
        ),
        migrations.AlterField(
            model_name='project',
            name='leader',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='led_projects',
                to=settings.AUTH_USER_MODEL,
                verbose_name='项目牵头负责人',
            ),
        ),
    ]
