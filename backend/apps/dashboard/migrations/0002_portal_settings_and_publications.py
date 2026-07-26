from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('singleton_key', models.CharField(default='default', max_length=20, unique=True)),
                ('team_name', models.CharField(default='创新团队', max_length=120, verbose_name='团队名称')),
                ('tagline', models.CharField(default='项目实践 · 赛事成长 · 成果沉淀', max_length=160, verbose_name='短标语')),
                ('summary', models.TextField(default='汇聚不同专业的成员，以真实项目协作积累经验，让过程可追踪、贡献可看见、成果可延续。', verbose_name='团队摘要')),
                ('about_title', models.CharField(default='从想法到落地，留下完整的团队记忆', max_length=160, verbose_name='团队介绍标题')),
                ('about_text', models.TextField(default='这里展示团队已经完成并经确认公开的项目、赛事和知识产权成果。', verbose_name='团队介绍')),
                ('logo_url', models.CharField(blank=True, default='', max_length=500, verbose_name='标志地址')),
                ('hero_image_url', models.CharField(blank=True, default='/portal/photos/lst/团队合影1.jpg', max_length=500, verbose_name='首图地址')),
                ('story_image_url', models.CharField(blank=True, default='/portal/photos/lst/挑战杯合影.jpg', max_length=500, verbose_name='赛事图片地址')),
                ('contact_email', models.EmailField(blank=True, default='', max_length=254, verbose_name='联系邮箱')),
                ('join_title', models.CharField(default='加入我们', max_length=160, verbose_name='加入我们标题')),
                ('join_message', models.TextField(blank=True, default='如果你愿意在真实项目中学习、协作和承担责任，欢迎联系我们。', verbose_name='加入我们说明')),
                ('join_url', models.CharField(blank=True, default='', max_length=500, verbose_name='加入链接')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_portal_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': '公开门户设置', 'db_table': 'portal_settings'},
        ),
        migrations.CreateModel(
            name='PortalPublication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.CharField(choices=[('project', '项目'), ('ip_application', '知识产权'), ('member', '成员')], max_length=30, verbose_name='内容类型')),
                ('object_id', models.PositiveBigIntegerField(verbose_name='对象 ID')),
                ('is_public', models.BooleanField(default=False, verbose_name='允许公开')),
                ('is_featured', models.BooleanField(default=False, verbose_name='重点展示')),
                ('member_consent', models.BooleanField(default=False, verbose_name='成员已授权')),
                ('display_order', models.IntegerField(default=0, verbose_name='展示顺序')),
                ('custom_title', models.CharField(blank=True, default='', max_length=200, verbose_name='公开标题')),
                ('custom_summary', models.TextField(blank=True, default='', verbose_name='公开摘要')),
                ('image_url', models.CharField(blank=True, default='', max_length=500, verbose_name='展示图片地址')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_portal_publications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '门户公开内容',
                'db_table': 'portal_publications',
                'ordering': ['-is_featured', 'display_order', 'id'],
                'unique_together': {('content_type', 'object_id')},
            },
        ),
    ]
