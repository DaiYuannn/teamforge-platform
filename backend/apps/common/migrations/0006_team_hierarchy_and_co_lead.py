import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_team_code_team_contact_email_team_is_active_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='child_teams',
                to='common.team',
                verbose_name='上级团队',
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='team_type',
            field=models.CharField(
                choices=[('organization', '总团队'), ('squad', '小团队')],
                default='organization',
                max_length=20,
                verbose_name='团队类型',
            ),
        ),
        migrations.AlterField(
            model_name='teammember',
            name='role',
            field=models.CharField(
                choices=[
                    ('owner', '负责人'),
                    ('co_lead', '共同负责人'),
                    ('admin', '团队管理员'),
                    ('teacher', '指导老师'),
                    ('member', '团队成员'),
                    ('advisor', '顾问'),
                    ('external', '外部协作者'),
                ],
                default='member',
                max_length=50,
                verbose_name='角色',
            ),
        ),
    ]
