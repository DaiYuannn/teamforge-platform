from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_userpreference_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='school',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='学校'),
        ),
    ]
