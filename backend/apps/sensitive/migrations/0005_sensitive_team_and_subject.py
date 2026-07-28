import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


PERSONAL_TYPES = {'id_card', 'bank_account', 'phone', 'address', 'signature'}


def backfill_sensitive_scope(apps, schema_editor):
    SensitiveData = apps.get_model('sensitive', 'SensitiveData')
    TeamMember = apps.get_model('common', 'TeamMember')

    for item in SensitiveData.objects.all().iterator():
        updates = {}
        if item.data_type in PERSONAL_TYPES and item.uploader_id:
            updates['subject_user_id'] = item.uploader_id
        owner_id = updates.get('subject_user_id') or item.uploader_id
        if owner_id:
            team_ids = list(
                TeamMember.objects.filter(
                    user_id=owner_id,
                    status='active',
                ).values_list('team_id', flat=True).distinct()[:2]
            )
            if len(team_ids) == 1:
                updates['team_id'] = team_ids[0]
        if updates:
            SensitiveData.objects.filter(pk=item.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_team_hierarchy_and_co_lead'),
        ('sensitive', '0004_protect_sensitive_file_attachments'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='sensitivedata',
            name='subject_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='personal_sensitive_data',
                to=settings.AUTH_USER_MODEL,
                verbose_name='资料所属成员',
            ),
        ),
        migrations.AddField(
            model_name='sensitivedata',
            name='team',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='sensitive_data',
                to='common.team',
                verbose_name='所属团队',
            ),
        ),
        migrations.RunPython(backfill_sensitive_scope, migrations.RunPython.noop),
    ]
