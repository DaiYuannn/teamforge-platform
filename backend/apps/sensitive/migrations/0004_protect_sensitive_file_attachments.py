from django.db import migrations


def protect_sensitive_file_attachments(apps, schema_editor):
    SensitiveData = apps.get_model('sensitive', 'SensitiveData')
    FileAsset = apps.get_model('files', 'FileAsset')
    FileShareLink = apps.get_model('files', 'FileShareLink')

    attachment_ids = list(SensitiveData.objects.exclude(
        file_attachment_id__isnull=True
    ).values_list('file_attachment_id', flat=True))
    FileAsset.objects.filter(pk__in=attachment_ids).update(level='sensitive')
    FileShareLink.objects.filter(
        file_id__in=attachment_ids,
        is_active=True,
    ).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0006_filesharelink'),
        ('sensitive', '0003_sensitiveaccessrequest_approval_opinion_and_more'),
    ]

    operations = [
        migrations.RunPython(
            protect_sensitive_file_attachments,
            migrations.RunPython.noop,
        ),
    ]
