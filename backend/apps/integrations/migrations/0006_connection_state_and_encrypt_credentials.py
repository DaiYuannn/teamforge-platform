from django.db import migrations, models


def encrypt_existing_credentials(apps, schema_editor):
    from common.encryption import get_field_cipher

    cipher = get_field_cipher()
    ExternalPlatform = apps.get_model('integrations', 'ExternalPlatform')
    GitRepository = apps.get_model('integrations', 'GitRepository')
    for platform in ExternalPlatform.objects.exclude(api_key='').iterator():
        if not platform.api_key.startswith('enc:v1:'):
            platform.api_key = 'enc:v1:' + cipher.encrypt(platform.api_key)
            platform.save(update_fields=['api_key'])
    for repository in GitRepository.objects.exclude(token='').iterator():
        if not repository.token.startswith('enc:v1:'):
            repository.token = 'enc:v1:' + cipher.encrypt(repository.token)
            repository.save(update_fields=['token'])


class Migration(migrations.Migration):
    dependencies = [('integrations', '0005_externalplatform_gitrepository')]
    operations = [
        migrations.AddField(model_name='externalplatform', name='connection_status', field=models.CharField(default='unchecked', max_length=20)),
        migrations.AddField(model_name='externalplatform', name='last_checked_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='externalplatform', name='last_synced_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='externalplatform', name='last_error', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='externalplatform', name='remote_metadata', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='gitrepository', name='connection_status', field=models.CharField(default='unchecked', max_length=20)),
        migrations.AddField(model_name='gitrepository', name='last_checked_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='gitrepository', name='last_synced_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='gitrepository', name='last_error', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='gitrepository', name='remote_commit', field=models.CharField(blank=True, default='', max_length=64)),
        migrations.RunPython(encrypt_existing_credentials, migrations.RunPython.noop),
    ]
