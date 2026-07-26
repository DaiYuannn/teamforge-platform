import django.core.validators
from django.db import migrations, models


THEME_CYCLE = ('blue', 'green', 'purple', 'orange')
THEME_PRIMARY_COLORS = {
    'blue': '#176b73',
    'green': '#2f6f4e',
    'purple': '#6f5a86',
    'orange': '#9a6238',
}
FIXED_DEMO_THEMES = {
    'admin': 'blue',
    'teacher1': 'purple',
    'teacher2': 'green',
    'approver': 'orange',
    'leader1': 'green',
    'leader2': 'blue',
    'leader3': 'purple',
    'leader4': 'orange',
    'leader5': 'green',
    'leader6': 'blue',
}


def assign_demo_themes(apps, schema_editor):
    User = apps.get_model('users', 'User')
    UserPreference = apps.get_model('users', 'UserPreference')

    UserPreference.objects.exclude(theme_color__in=THEME_CYCLE).update(
        theme_color='blue'
    )
    for theme, primary_color in THEME_PRIMARY_COLORS.items():
        UserPreference.objects.filter(theme_color=theme).update(
            primary_color=primary_color
        )

    for user in User.objects.filter(email__endswith='@demo.com').iterator():
        account = user.email.split('@', 1)[0].lower()
        theme = FIXED_DEMO_THEMES.get(account)
        if theme is None:
            suffix = ''.join(character for character in account if character.isdigit())
            index = int(suffix) - 1 if suffix else user.pk
            theme = THEME_CYCLE[index % len(THEME_CYCLE)]
        UserPreference.objects.update_or_create(
            user_id=user.pk,
            defaults={
                'theme_color': theme,
                'primary_color': THEME_PRIMARY_COLORS[theme],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_customrole_ipblocklist_loginattempt_twofactorsecret_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpreference',
            name='theme_color',
            field=models.CharField(
                choices=[
                    ('blue', '蓝色'),
                    ('green', '绿色'),
                    ('purple', '紫色'),
                    ('orange', '橙色'),
                ],
                default='blue',
                max_length=20,
                verbose_name='主题色',
            ),
        ),
        migrations.AddField(
            model_name='userpreference',
            name='primary_color',
            field=models.CharField(
                default='#176b73',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        message='主色必须是完整的六位十六进制颜色，例如 #176b73',
                        regex='^#[0-9A-Fa-f]{6}$',
                    )
                ],
                verbose_name='界面主色',
            ),
        ),
        migrations.RunPython(assign_demo_themes, migrations.RunPython.noop),
    ]
