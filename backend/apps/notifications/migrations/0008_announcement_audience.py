from django.db import migrations, models
import django.db.models.deletion


def populate_announcement_audience(apps, schema_editor):
    Announcement = apps.get_model('notifications', 'Announcement')
    Team = apps.get_model('common', 'Team')
    TeamMember = apps.get_model('common', 'TeamMember')

    root_ids = list(
        Team.objects.filter(parent__isnull=True).values_list('id', flat=True)
    )
    sole_root_id = root_ids[0] if len(root_ids) == 1 else None

    for announcement in Announcement.objects.all().iterator():
        audience = 'public' if announcement.is_public else 'organization'
        organization_id = None
        if announcement.author_id:
            membership_rows = TeamMember.objects.filter(
                user_id=announcement.author_id,
                status__in=['active', 'on_leave'],
            ).values_list('team_id', 'team__parent_id')
            author_root_ids = {
                parent_id or team_id
                for team_id, parent_id in membership_rows
            }
            owner_rows = Team.objects.filter(
                owner_id=announcement.author_id,
            ).values_list('id', 'parent_id')
            author_root_ids.update(
                parent_id or team_id
                for team_id, parent_id in owner_rows
            )
            if len(author_root_ids) == 1:
                organization_id = next(iter(author_root_ids))
        if organization_id is None:
            organization_id = sole_root_id
        Announcement.objects.filter(pk=announcement.pk).update(
            audience=audience,
            organization_id=organization_id,
        )


def reverse_announcement_audience(apps, schema_editor):
    Announcement = apps.get_model('notifications', 'Announcement')
    Announcement.objects.filter(audience='public').update(is_public=True)
    Announcement.objects.exclude(audience='public').update(is_public=False)


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_team_hierarchy_and_co_lead'),
        ('projects', '0009_project_teams_visibility'),
        ('notifications', '0007_announcement_resources'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='audience',
            field=models.CharField(
                choices=[
                    ('organization', '全实践团队'),
                    ('teams', '指定小团队'),
                    ('projects', '指定项目'),
                    ('public', '互联网公开'),
                ],
                db_index=True,
                default='organization',
                max_length=20,
                verbose_name='发布范围',
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                help_text='公告所属的根团队，用于不同实践团队之间的数据隔离',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='organization_announcements',
                to='common.team',
                verbose_name='所属实践团队',
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='target_projects',
            field=models.ManyToManyField(
                blank=True,
                related_name='targeted_announcements',
                to='projects.project',
                verbose_name='目标项目',
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='target_teams',
            field=models.ManyToManyField(
                blank=True,
                related_name='targeted_announcements',
                to='common.team',
                verbose_name='目标小团队',
            ),
        ),
        migrations.RunPython(
            populate_announcement_audience,
            reverse_announcement_audience,
        ),
    ]
