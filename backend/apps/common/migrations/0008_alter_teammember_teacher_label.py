from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0007_activity_organization_and_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teammember',
            name='role',
            field=models.CharField(
                choices=[
                    ('owner', '负责人'),
                    ('co_lead', '共同负责人'),
                    ('admin', '团队管理员'),
                    ('teacher', '查看老师（只读）'),
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
