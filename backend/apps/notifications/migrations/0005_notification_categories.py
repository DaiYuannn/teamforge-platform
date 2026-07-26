from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_add_announcement_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('system', '系统通知'),
                    ('project', '项目通知'),
                    ('task', '任务通知'),
                    ('finance', '经费通知'),
                    ('competition', '比赛通知'),
                    ('contribution', '贡献通知'),
                    ('ip', '知识产权通知'),
                    ('sensitive', '敏感资料通知'),
                    ('schedule', '工时通知'),
                    ('report', '报表通知'),
                    ('announcement', '公告'),
                ],
                default='system',
                max_length=20,
                verbose_name='通知类型',
            ),
        ),
    ]
