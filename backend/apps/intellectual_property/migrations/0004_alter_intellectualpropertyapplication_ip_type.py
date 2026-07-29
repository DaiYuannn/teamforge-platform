from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('intellectual_property', '0003_multi_project_candidates_status_note'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intellectualpropertyapplication',
            name='ip_type',
            field=models.CharField(
                choices=[
                    ('software_copyright', '软件著作权'),
                    ('invention_patent', '发明专利'),
                    ('utility_model', '实用新型专利'),
                    ('design_patent', '外观设计专利'),
                    ('novelty_search', '科技查新'),
                    ('paper', '论文成果'),
                    ('other', '其他'),
                ],
                default='software_copyright',
                max_length=30,
                verbose_name='成果类型',
            ),
        ),
    ]
