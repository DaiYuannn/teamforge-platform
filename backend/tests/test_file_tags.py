"""
N10: 文件标签（File Tags）测试
- 模型层：FileTag / FileTagRelation 创建与唯一约束
- API 层：标签 CRUD、分配/取消标签、按文件查询标签
- 权限验证
"""
import pytest
from django.db import IntegrityError


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.model
@pytest.mark.django_db
class TestFileTagModel:
    """文件标签模型测试"""

    def test_create_tag(self, make_user):
        """创建标签"""
        from apps.files.tag_models import FileTag
        user = make_user()
        tag = FileTag.objects.create(name='重要', color='#F56C6C', created_by=user)
        assert tag.id is not None
        assert tag.name == '重要'
        assert tag.color == '#F56C6C'
        assert tag.created_by == user
        assert tag.project is None

    def test_tag_default_color(self, make_user):
        """标签默认颜色"""
        from apps.files.tag_models import FileTag
        tag = FileTag.objects.create(name='默认色')
        assert tag.color == '#409EFF'

    def test_tag_with_project(self, make_project, make_user):
        """带项目的标签"""
        from apps.files.tag_models import FileTag
        project = make_project()
        tag = FileTag.objects.create(name='项目标签', project=project, created_by=make_user())
        assert tag.project == project

    def test_tag_unique_together_with_project(self, make_project, make_user):
        """同一项目下标签名唯一"""
        from apps.files.tag_models import FileTag
        project = make_project()
        FileTag.objects.create(name='重复', project=project, created_by=make_user())
        with pytest.raises(IntegrityError):
            FileTag.objects.create(name='重复', project=project, created_by=make_user())

    def test_tag_unique_together_different_project(self, make_project, make_user):
        """不同项目下可以有同名标签"""
        from apps.files.tag_models import FileTag
        p1 = make_project()
        p2 = make_project()
        FileTag.objects.create(name='同名', project=p1, created_by=make_user())
        tag2 = FileTag.objects.create(name='同名', project=p2, created_by=make_user())
        assert tag2.id is not None

    def test_tag_relation_create(self, make_file, make_user):
        """创建文件-标签关联"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        tag = FileTag.objects.create(name='设计稿', created_by=make_user())
        rel = FileTagRelation.objects.create(file=f, tag=tag)
        assert rel.id is not None
        assert rel.file == f
        assert rel.tag == tag

    def test_tag_relation_unique(self, make_file, make_user):
        """同一文件同一标签关联唯一"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        tag = FileTag.objects.create(name='唯一', created_by=make_user())
        FileTagRelation.objects.create(file=f, tag=tag)
        with pytest.raises(IntegrityError):
            FileTagRelation.objects.create(file=f, tag=tag)

    def test_tag_cascade_delete_with_file(self, make_file, make_user):
        """删除文件时级联删除关联"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        tag = FileTag.objects.create(name='级联', created_by=make_user())
        FileTagRelation.objects.create(file=f, tag=tag)
        assert FileTagRelation.objects.count() == 1
        f.delete()
        assert FileTagRelation.objects.count() == 0
        # 标签本身仍在
        assert FileTag.objects.filter(id=tag.id).exists()

    def test_tag_cascade_delete_tag(self, make_file, make_user):
        """删除标签时级联删除关联"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        tag = FileTag.objects.create(name='删标签', created_by=make_user())
        FileTagRelation.objects.create(file=f, tag=tag)
        assert FileTagRelation.objects.count() == 1
        tag.delete()
        assert FileTagRelation.objects.count() == 0


@pytest.mark.api
@pytest.mark.django_db
class TestFileTagCRUDAPI:
    """文件标签 CRUD API 测试"""

    def test_create_tag(self, teacher_client):
        """创建标签"""
        resp = teacher_client.post('/api/v1/files/tags/', {
            'name': '重要文档',
            'color': '#F56C6C',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['name'] == '重要文档'
        assert data['color'] == '#F56C6C'
        assert data['created_by'] == teacher_client.user.id
        assert data['id'] is not None

    def test_list_tags(self, teacher_client, make_user):
        """标签列表"""
        from apps.files.tag_models import FileTag
        FileTag.objects.create(name='标签1', created_by=make_user())
        FileTag.objects.create(name='标签2', created_by=make_user())
        resp = teacher_client.get('/api/v1/files/tags/')
        assert resp.status_code == 200
        data = extract_data(resp)
        # DefaultRouter list 返回列表或分页
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) >= 2

    def test_retrieve_tag(self, teacher_client, make_user):
        """标签详情"""
        from apps.files.tag_models import FileTag
        tag = FileTag.objects.create(name='详情', created_by=make_user())
        resp = teacher_client.get(f'/api/v1/files/tags/{tag.id}/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['name'] == '详情'

    def test_update_tag(self, teacher_client, make_user):
        """更新标签"""
        from apps.files.tag_models import FileTag
        tag = FileTag.objects.create(name='原名', created_by=make_user())
        resp = teacher_client.patch(f'/api/v1/files/tags/{tag.id}/', {
            'name': '新名',
            'color': '#67C23A',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['name'] == '新名'
        assert data['color'] == '#67C23A'
        tag.refresh_from_db()
        assert tag.name == '新名'

    def test_delete_tag(self, teacher_client, make_user):
        """删除标签"""
        from apps.files.tag_models import FileTag
        tag = FileTag.objects.create(name='删除', created_by=make_user())
        resp = teacher_client.delete(f'/api/v1/files/tags/{tag.id}/')
        assert resp.status_code == 200
        assert not FileTag.objects.filter(id=tag.id).exists()

    def test_filter_by_project(self, teacher_client, make_project, make_user):
        """按项目过滤标签"""
        from apps.files.tag_models import FileTag
        p = make_project()
        FileTag.objects.create(name='项目内', project=p, created_by=make_user())
        FileTag.objects.create(name='全局', created_by=make_user())
        resp = teacher_client.get(f'/api/v1/files/tags/?project={p.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        names = [r['name'] for r in results]
        assert '项目内' in names
        assert '全局' not in names

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证不能访问标签"""
        resp = api_client.get('/api/v1/files/tags/')
        assert resp.status_code == 401


@pytest.mark.api
@pytest.mark.django_db
class TestFileTagAssignAPI:
    """文件标签分配/取消测试"""

    def test_assign_tags(self, teacher_client, make_file, make_user):
        """给文件分配标签"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        t1 = FileTag.objects.create(name='标签A', created_by=make_user())
        t2 = FileTag.objects.create(name='标签B', created_by=make_user())

        resp = teacher_client.post('/api/v1/files/tags/assign/', {
            'file': f.id,
            'tags': [t1.id, t2.id],
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['assigned'] == 2
        assert FileTagRelation.objects.filter(file=f).count() == 2

    def test_assign_idempotent(self, teacher_client, make_file, make_user):
        """重复分配标签不报错（幂等）"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        t1 = FileTag.objects.create(name='幂等', created_by=make_user())
        teacher_client.post('/api/v1/files/tags/assign/', {
            'file': f.id, 'tags': [t1.id],
        }, format='json')
        resp = teacher_client.post('/api/v1/files/tags/assign/', {
            'file': f.id, 'tags': [t1.id],
        }, format='json')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['assigned'] == 0
        assert FileTagRelation.objects.filter(file=f).count() == 1

    def test_unassign_tags(self, teacher_client, make_file, make_user):
        """取消文件标签"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        t1 = FileTag.objects.create(name='取消', created_by=make_user())
        FileTagRelation.objects.create(file=f, tag=t1)
        assert FileTagRelation.objects.filter(file=f).count() == 1

        resp = teacher_client.post('/api/v1/files/tags/unassign/', {
            'file': f.id, 'tags': [t1.id],
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['unassigned'] == 1
        assert FileTagRelation.objects.filter(file=f).count() == 0

    def test_assign_nonexistent_file(self, teacher_client, make_user):
        """分配标签到不存在的文件"""
        from apps.files.tag_models import FileTag
        t1 = FileTag.objects.create(name='不存在文件', created_by=make_user())
        resp = teacher_client.post('/api/v1/files/tags/assign/', {
            'file': 999999, 'tags': [t1.id],
        }, format='json')
        assert resp.status_code == 404

    def test_assign_invalid_payload(self, teacher_client):
        """无效请求体"""
        resp = teacher_client.post('/api/v1/files/tags/assign/', {
            'file': 1,  # 缺少 tags
        }, format='json')
        assert resp.status_code == 400

    def test_by_file(self, teacher_client, make_file, make_user):
        """按文件查询标签"""
        from apps.files.tag_models import FileTag, FileTagRelation
        f = make_file()
        t1 = FileTag.objects.create(name='查询1', color='#111111', created_by=make_user())
        t2 = FileTag.objects.create(name='查询2', color='#222222', created_by=make_user())
        FileTagRelation.objects.create(file=f, tag=t1)
        FileTagRelation.objects.create(file=f, tag=t2)

        resp = teacher_client.get(f'/api/v1/files/tags/by-file/?file={f.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 2
        tag_names = [d['tag_name'] for d in data]
        assert '查询1' in tag_names
        assert '查询2' in tag_names
        # 包含颜色信息
        colors = [d['tag_color'] for d in data]
        assert '#111111' in colors

    def test_by_file_empty(self, teacher_client, make_file):
        """文件无标签"""
        f = make_file()
        resp = teacher_client.get(f'/api/v1/files/tags/by-file/?file={f.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 0

    def test_by_file_missing_param(self, teacher_client):
        """缺少 file 参数"""
        resp = teacher_client.get('/api/v1/files/tags/by-file/')
        assert resp.status_code == 400
