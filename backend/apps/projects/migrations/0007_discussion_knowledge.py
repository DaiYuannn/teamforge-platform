"""
N27/N28: 讨论区 + 知识库 模型迁移
- DiscussionTopic: 讨论主题
- DiscussionReply: 讨论回复
- KnowledgeArticle: 知识库文章
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_milestone_projectrisk_projecttemplate'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ===== N27: 讨论区 =====
        migrations.CreateModel(
            name='DiscussionTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='标题')),
                ('content', models.TextField(verbose_name='内容')),
                ('is_pinned', models.BooleanField(default=False, verbose_name='置顶')),
                ('is_closed', models.BooleanField(default=False, verbose_name='已关闭')),
                ('view_count', models.IntegerField(default=0, verbose_name='浏览数')),
                ('reply_count', models.IntegerField(default=0, verbose_name='回复数')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discussions', to='projects.project', verbose_name='项目')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discussion_topics', to=settings.AUTH_USER_MODEL, verbose_name='发起人')),
            ],
            options={
                'verbose_name': '讨论主题',
                'verbose_name_plural': '讨论主题',
                'db_table': 'discussion_topics',
                'ordering': ['-is_pinned', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DiscussionReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='回复内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='projects.discussiontopic', verbose_name='主题')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discussion_replies', to=settings.AUTH_USER_MODEL, verbose_name='回复人')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='projects.discussionreply', verbose_name='父回复')),
            ],
            options={
                'verbose_name': '讨论回复',
                'verbose_name_plural': '讨论回复',
                'db_table': 'discussion_replies',
                'ordering': ['created_at'],
            },
        ),
        # ===== N28: 知识库 =====
        migrations.CreateModel(
            name='KnowledgeArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='标题')),
                ('content', models.TextField(verbose_name='内容')),
                ('category', models.CharField(choices=[('guide', '指南'), ('template', '模板'), ('faq', '常见问题'), ('experience', '经验分享'), ('other', '其他')], default='other', max_length=20, verbose_name='类别')),
                ('tags', models.CharField(blank=True, default='', max_length=500, verbose_name='标签')),
                ('view_count', models.IntegerField(default=0, verbose_name='浏览数')),
                ('is_published', models.BooleanField(default=True, verbose_name='已发布')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_articles', to='projects.project', verbose_name='关联项目')),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='knowledge_articles', to=settings.AUTH_USER_MODEL, verbose_name='作者')),
            ],
            options={
                'verbose_name': '知识库文章',
                'verbose_name_plural': '知识库文章',
                'db_table': 'knowledge_articles',
                'ordering': ['-created_at'],
            },
        ),
    ]
