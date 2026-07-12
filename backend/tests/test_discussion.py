"""
N27: 讨论区（Discussion Board）测试
- 模型层：DiscussionTopic / DiscussionReply 创建与关系
- API 层：主题 CRUD、回复、置顶/关闭、浏览数、回复数
- 权限验证
"""
import pytest

from apps.projects.discussion_models import DiscussionTopic, DiscussionReply

DISCUSSION_URL = '/api/v1/projects/discussions/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def extract_results(resp):
    data = extract_data(resp)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return data


@pytest.mark.model
@pytest.mark.django_db
class TestDiscussionModel:
    """讨论区模型测试"""

    def test_create_topic(self, make_project, make_user):
        """创建讨论主题"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题1', content='内容1', author=author,
        )
        assert topic.id is not None
        assert topic.is_pinned is False
        assert topic.is_closed is False
        assert topic.view_count == 0
        assert topic.reply_count == 0

    def test_topic_default_ordering_pinned_first(self, make_project, make_user):
        """置顶主题排在前面"""
        project = make_project()
        author = make_user()
        t1 = DiscussionTopic.objects.create(
            project=project, title='普通主题', content='a', author=author,
        )
        t2 = DiscussionTopic.objects.create(
            project=project, title='置顶主题', content='b', author=author,
            is_pinned=True,
        )
        topics = list(DiscussionTopic.objects.all())
        assert topics[0] == t2
        assert topics[1] == t1

    def test_create_reply(self, make_project, make_user):
        """创建回复"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        reply = DiscussionReply.objects.create(
            topic=topic, author=author, content='第一条回复',
        )
        assert reply.id is not None
        assert reply.parent is None

    def test_nested_reply(self, make_project, make_user):
        """嵌套回复（父回复）"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        parent = DiscussionReply.objects.create(
            topic=topic, author=author, content='父回复',
        )
        child = DiscussionReply.objects.create(
            topic=topic, author=author, content='子回复', parent=parent,
        )
        assert child.parent == parent
        assert parent.children.count() == 1

    def test_refresh_reply_count(self, make_project, make_user):
        """刷新回复数"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        DiscussionReply.objects.create(topic=topic, author=author, content='r1')
        DiscussionReply.objects.create(topic=topic, author=author, content='r2')
        topic.refresh_reply_count()
        assert topic.reply_count == 2

    def test_cascade_delete_topic_replies(self, make_project, make_user):
        """删除主题时级联删除回复"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        DiscussionReply.objects.create(topic=topic, author=author, content='r1')
        assert DiscussionReply.objects.count() == 1
        topic.delete()
        assert DiscussionReply.objects.count() == 0

    def test_related_name_discussions(self, make_project, make_user):
        """反向关系 project.discussions 可访问"""
        project = make_project()
        author = make_user()
        DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        assert project.discussions.count() == 1


@pytest.mark.api
@pytest.mark.django_db
class TestDiscussionAPI:
    """讨论区 API 测试"""

    def test_create_topic(self, auth_client, make_project):
        """认证用户可以创建讨论主题"""
        project = make_project()
        resp = auth_client.post(DISCUSSION_URL, {
            'project': project.id,
            'title': 'API创建主题',
            'content': '这是内容',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == 'API创建主题'
        assert data['author'] == auth_client.user.id

    def test_list_topics(self, member_client, make_project, make_user):
        """普通成员可以查看讨论列表"""
        project = make_project()
        author = make_user()
        DiscussionTopic.objects.create(
            project=project, title='列表主题', content='内容', author=author,
        )
        resp = member_client.get(DISCUSSION_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_topics_by_project(self, member_client, make_project, make_user):
        """按项目过滤讨论主题"""
        p1 = make_project()
        p2 = make_project()
        author = make_user()
        DiscussionTopic.objects.create(project=p1, title='A', content='c', author=author)
        DiscussionTopic.objects.create(project=p2, title='B', content='c', author=author)
        resp = member_client.get(f'{DISCUSSION_URL}?project={p1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['project'] == p1.id for r in results)

    def test_retrieve_topic_increments_view(self, auth_client, make_project, make_user):
        """获取详情时增加浏览数"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='详情', content='内容', author=author,
        )
        assert topic.view_count == 0
        resp = auth_client.get(f'{DISCUSSION_URL}{topic.id}/')
        assert resp.status_code == 200, resp.json()
        topic.refresh_from_db()
        assert topic.view_count == 1

    def test_reply_to_topic(self, auth_client, make_project, make_user):
        """回复讨论主题"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        resp = auth_client.post(f'{DISCUSSION_URL}{topic.id}/reply/', {
            'content': '这是一条回复',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['content'] == '这是一条回复'
        assert data['author'] == auth_client.user.id
        topic.refresh_from_db()
        assert topic.reply_count == 1

    def test_reply_to_closed_topic_fails(self, auth_client, make_project, make_user):
        """关闭的主题不能回复"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
            is_closed=True,
        )
        resp = auth_client.post(f'{DISCUSSION_URL}{topic.id}/reply/', {
            'content': '尝试回复',
        }, format='json')
        assert resp.status_code == 400

    def test_reply_empty_content_fails(self, auth_client, make_project, make_user):
        """空内容回复失败"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        resp = auth_client.post(f'{DISCUSSION_URL}{topic.id}/reply/', {
            'content': '',
        }, format='json')
        assert resp.status_code == 400

    def test_nested_reply_via_api(self, auth_client, make_project, make_user):
        """通过 API 创建嵌套回复"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        # 先创建父回复
        parent = DiscussionReply.objects.create(
            topic=topic, author=author, content='父回复',
        )
        resp = auth_client.post(f'{DISCUSSION_URL}{topic.id}/reply/', {
            'content': '子回复',
            'parent': parent.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['parent'] == parent.id

    def test_get_replies_list(self, member_client, make_project, make_user):
        """获取主题回复列表"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        DiscussionReply.objects.create(topic=topic, author=author, content='r1')
        DiscussionReply.objects.create(topic=topic, author=author, content='r2')
        resp = member_client.get(f'{DISCUSSION_URL}{topic.id}/replies/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 2

    def test_toggle_pin_by_teacher(self, teacher_client, make_project, make_user):
        """老师可以置顶主题"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        resp = teacher_client.post(f'{DISCUSSION_URL}{topic.id}/toggle-pin/')
        assert resp.status_code == 200, resp.json()
        topic.refresh_from_db()
        assert topic.is_pinned is True

    def test_toggle_pin_by_member_forbidden(self, auth_client, make_project, make_user):
        """普通成员不能置顶"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        resp = auth_client.post(f'{DISCUSSION_URL}{topic.id}/toggle-pin/')
        assert resp.status_code == 403

    def test_toggle_close_by_teacher(self, teacher_client, make_project, make_user):
        """老师可以关闭主题"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='主题', content='内容', author=author,
        )
        resp = teacher_client.post(f'{DISCUSSION_URL}{topic.id}/toggle-close/')
        assert resp.status_code == 200, resp.json()
        topic.refresh_from_db()
        assert topic.is_closed is True

    def test_update_topic_by_author(self, auth_client, make_project):
        """作者可以更新自己的主题"""
        project = make_project()
        topic = DiscussionTopic.objects.create(
            project=project, title='原标题', content='原内容', author=auth_client.user,
        )
        resp = auth_client.patch(f'{DISCUSSION_URL}{topic.id}/', {
            'title': '新标题',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['title'] == '新标题'

    def test_delete_topic_by_author(self, auth_client, make_project):
        """作者可以删除自己的主题"""
        project = make_project()
        topic = DiscussionTopic.objects.create(
            project=project, title='待删除', content='内容', author=auth_client.user,
        )
        resp = auth_client.delete(f'{DISCUSSION_URL}{topic.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not DiscussionTopic.objects.filter(id=topic.id).exists()

    def test_update_topic_by_non_author_forbidden(self, auth_client, make_project, make_user):
        """非作者不能更新他人主题"""
        project = make_project()
        author = make_user()
        topic = DiscussionTopic.objects.create(
            project=project, title='他人主题', content='内容', author=author,
        )
        resp = auth_client.patch(f'{DISCUSSION_URL}{topic.id}/', {
            'title': '篡改',
        }, format='json')
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证不能访问"""
        resp = api_client.get(DISCUSSION_URL)
        assert resp.status_code == 401
