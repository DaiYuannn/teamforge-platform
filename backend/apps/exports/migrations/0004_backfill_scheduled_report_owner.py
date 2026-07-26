from django.db import migrations


def backfill_scheduled_report_owner(apps, schema_editor):
    ScheduledReport = apps.get_model('exports', 'ScheduledReport')
    for schedule in (
        ScheduledReport.objects.filter(created_by__isnull=True)
        .select_related('report')
        .iterator()
    ):
        if schedule.report.created_by_id:
            schedule.created_by_id = schedule.report.created_by_id
            schedule.save(update_fields=['created_by'])


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0003_scheduledreport_created_by_and_more'),
    ]

    operations = [
        migrations.RunPython(
            backfill_scheduled_report_owner,
            migrations.RunPython.noop,
        ),
    ]
