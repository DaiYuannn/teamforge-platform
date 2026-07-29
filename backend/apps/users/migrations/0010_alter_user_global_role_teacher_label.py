from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_user_school'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='global_role',
            field=models.CharField(
                choices=[
                    ('sys_admin', '系统管理员'),
                    ('teacher', '操作老师'),
                    ('member', '普通成员'),
                    ('sens_approver', '敏感审批人'),
                ],
                default='member',
                max_length=20,
                verbose_name='全局角色',
            ),
        ),
    ]
