"""
N04 任务评论模块测试
- 创建 / 回复 / 列表 / 更新 / 删除
- 权限：所有认证用户可评论，仅作者或老师/管理员可编辑删除
"""
import pytest

from apps.tasks.comment_models import TaskComment

COMMENT_URL = '/api/v1/tasks/comments/'


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


@pytest.mark.api
@pytest.mark.django_db
class TestTaskCommentAPI:
    """任务评论 API 测试"""

    def test_create_comment_by_member(self, member_client, make_task):
        """普通成员可以发表评论"""
        task = make_task()
        resp = member_client.post(COMMENT_URL, {
            'task': task.id,
            'content': '这是一条评论',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['content'] == '这是一条评论'
        assert data['author'] == member_client.user.id

    def test_create_reply(self, member_client, make_task):
        """可以回复评论（多级）"""
        task = make_task()
        parent = TaskComment.objects.create(
            task=task, author=member_client.user, content='父评论'
        )
        resp = member_client.post(COMMENT_URL, {
            'task': task.id,
            'content': '回复内容',
            'parent': parent.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['parent'] == parent.id

    def test_list_comments(self, member_client, make_task):
        """查看评论列表"""
        task = make_task()
        TaskComment.objects.create(task=task, author=member_client.user, content='评论A')
        resp = member_client.get(COMMENT_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_comments_by_task(self, member_client, make_task):
        """按任务筛选评论"""
        task1 = make_task()
        task2 = make_task()
        TaskComment.objects.create(task=task1, author=member_client.user, content='属于task1')
        TaskComment.objects.create(task=task2, author=member_client.user, content='属于task2')
        resp = member_client.get(f'{COMMENT_URL}?task={task1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['task'] == task1.id for r in results)

    def test_update_own_comment(self, member_client, make_task):
        """作者可以更新自己的评论"""
        task = make_task()
        comment = TaskComment.objects.create(
            task=task, author=member_client.user, content='原内容'
        )
        resp = member_client.patch(f'{COMMENT_URL}{comment.id}/', {
            'content': '更新内容',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['content'] == '更新内容'

    def test_cannot_update_others_comment(self, member_client, make_task, make_user):
        """不能更新他人评论"""
        task = make_task()
        other = make_user(email='other_cmt@test.com')
        comment = TaskComment.objects.create(
            task=task, author=other, content='他人评论'
        )
        resp = member_client.patch(f'{COMMENT_URL}{comment.id}/', {
            'content': '成员尝试修改',
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_delete_own_comment(self, member_client, make_task):
        """作者可以删除自己的评论"""
        task = make_task()
        comment = TaskComment.objects.create(
            task=task, author=member_client.user, content='待删除'
        )
        resp = member_client.delete(f'{COMMENT_URL}{comment.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not TaskComment.objects.filter(id=comment.id).exists()

    def test_teacher_can_delete_any_comment(self, teacher_client, make_task, make_user):
        """老师可以删除任何评论"""
        task = make_task()
        other = make_user(email='other_cmt2@test.com')
        comment = TaskComment.objects.create(
            task=task, author=other, content='他人评论'
        )
        resp = teacher_client.delete(f'{COMMENT_URL}{comment.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not TaskComment.objects.filter(id=comment.id).exists()


@pytest.mark.model
@pytest.mark.django_db
class TestTaskCommentModel:
    """任务评论模型测试"""

    def test_default_ordering(self, make_task, make_user):
        """评论按创建时间倒序"""
        # 模型 Meta 配置为按 created_at 倒序
        assert TaskComment._meta.ordering == ['-created_at']

    def test_reply_related_name(self, make_task, make_user):
        """回复通过 replies 反向关联"""
        task = make_task()
        user = make_user()
        parent = TaskComment.objects.create(task=task, author=user, content='父')
        reply = TaskComment.objects.create(
            task=task, author=user, content='回复', parent=parent
        )
        assert parent.replies.count() == 1
        assert parent.replies.first().id == reply.id
