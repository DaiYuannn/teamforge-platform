from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0007_userpreference_schedule_end_and_more')]

    operations = [
        migrations.AddField(
            model_name='userpreference',
            name='language',
            field=models.CharField(
                choices=[('zh-CN', '简体中文'), ('en', 'English')],
                default='zh-CN',
                max_length=10,
                verbose_name='界面语言',
            ),
        ),
    ]
