import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0003_competitionaward'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CompetitionParticipant',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'role',
                    models.CharField(
                        choices=[
                            ('leader', '比赛负责人'),
                            ('member', '参赛成员'),
                            ('advisor', '指导成员'),
                        ],
                        default='member',
                        max_length=20,
                        verbose_name='比赛角色',
                    ),
                ),
                (
                    'participation_status',
                    models.CharField(
                        choices=[
                            ('planned', '拟参赛'),
                            ('confirmed', '已确认'),
                            ('withdrawn', '已退出'),
                        ],
                        db_index=True,
                        default='planned',
                        max_length=20,
                        verbose_name='参与状态',
                    ),
                ),
                ('responsibility', models.TextField(blank=True, default='', verbose_name='比赛分工')),
                ('joined_at', models.DateTimeField(auto_now_add=True, verbose_name='加入时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                (
                    'competition',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='participants',
                        to='competitions.competition',
                        verbose_name='比赛',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='competition_participant_records',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='成员',
                    ),
                ),
            ],
            options={
                'verbose_name': '比赛参赛成员',
                'verbose_name_plural': '比赛参赛成员',
                'db_table': 'competition_participants',
                'ordering': ['role', 'joined_at', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='competitionparticipant',
            constraint=models.UniqueConstraint(
                fields=('competition', 'user'),
                name='uniq_competition_participant_user',
            ),
        ),
        migrations.AddField(
            model_name='competition',
            name='participant_users',
            field=models.ManyToManyField(
                blank=True,
                related_name='competition_participations',
                through='competitions.CompetitionParticipant',
                to=settings.AUTH_USER_MODEL,
                verbose_name='参赛成员',
            ),
        ),
    ]
