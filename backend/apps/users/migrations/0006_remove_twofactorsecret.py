from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_exit_reason_user_handover_notes_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TwoFactorSecret',
        ),
    ]
