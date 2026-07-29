import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_team_hierarchy_and_co_lead'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='activities',
                to='common.team',
                verbose_name='所属实践团队',
            ),
        ),
        migrations.AlterField(
            model_name='activity',
            name='activity_type',
            field=models.CharField(
                choices=[
                    ('project_created', '创建项目'),
                    ('project_updated', '更新项目'),
                    ('project_closed', '关闭项目'),
                    ('task_created', '创建任务'),
                    ('task_completed', '完成任务'),
                    ('task_updated', '更新任务'),
                    ('file_uploaded', '上传文件'),
                    ('comment_created', '发表评论'),
                    ('member_joined', '成员加入'),
                    ('member_left', '成员离开'),
                    ('competition_created', '创建比赛参赛条目'),
                    ('competition_updated', '更新比赛参赛条目'),
                    ('competition_awarded', '登记比赛获奖'),
                    ('finance_expense', '登记或更新支出'),
                    ('finance_payment', '完成经费付款'),
                    ('finance_income', '登记或更新收入'),
                    ('ip_created', '创建知识产权成果'),
                    ('ip_updated', '更新知识产权成果'),
                    ('ip_authorized', '知识产权成果授权'),
                    ('announcement_published', '发布公告'),
                ],
                max_length=50,
                verbose_name='动态类型',
            ),
        ),
    ]
