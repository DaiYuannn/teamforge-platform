"""
N31: 文件哈希（File Hash）测试
- 模型层：SHA-256 哈希自动计算
- API 层：check_duplicate 查重
- 相同内容文件哈希相同
- 虚拟路径文件不崩溃
"""
import hashlib
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_image_bytes(color='red', size=(100, 100)):
    """生成小型 PNG 图片字节"""
    from PIL import Image
    img = Image.new('RGB', size, color=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def make_text_bytes(text=b'hello world'):
    """生成文本文件字节"""
    return text


@pytest.mark.model
@pytest.mark.django_db
class TestFileHashModel:
    """文件哈希模型测试"""

    def test_hash_computed_on_upload(self, make_project, make_user):
        """上传文件后自动计算 SHA-256 哈希"""
        from apps.files.models import FileAsset
        content = b'test file content for hashing'
        upload = SimpleUploadedFile('test.txt', content, content_type='text/plain')
        asset = FileAsset.objects.create(
            project=make_project(), name='test.txt', file=upload,
            level='public', uploader=make_user(),
        )
        expected = hashlib.sha256(content).hexdigest()
        assert asset.file_hash == expected

    def test_same_content_same_hash(self, make_project, make_user):
        """相同内容产生相同哈希"""
        from apps.files.models import FileAsset
        content = b'identical content'
        a1 = FileAsset.objects.create(
            project=make_project(), name='a.txt',
            file=SimpleUploadedFile('a.txt', content), uploader=make_user(),
        )
        a2 = FileAsset.objects.create(
            project=make_project(), name='b.txt',
            file=SimpleUploadedFile('b.txt', content), uploader=make_user(),
        )
        assert a1.file_hash == a2.file_hash
        assert a1.file_hash != ''

    def test_different_content_different_hash(self, make_project, make_user):
        """不同内容产生不同哈希"""
        from apps.files.models import FileAsset
        a1 = FileAsset.objects.create(
            project=make_project(), name='a.txt',
            file=SimpleUploadedFile('a.txt', b'content A'), uploader=make_user(),
        )
        a2 = FileAsset.objects.create(
            project=make_project(), name='b.txt',
            file=SimpleUploadedFile('b.txt', b'content B'), uploader=make_user(),
        )
        assert a1.file_hash != a2.file_hash

    def test_dummy_path_no_crash(self, make_project, make_user):
        """虚拟路径文件（哈希不可计算）不崩溃，哈希为空"""
        from apps.files.models import FileAsset
        asset = FileAsset.objects.create(
            project=make_project(), name='dummy.pdf',
            file='dummy/path.pdf', level='public', uploader=make_user(),
        )
        # 文件不存在于磁盘，哈希应为空
        assert asset.file_hash == ''

    def test_hash_is_sha256_length(self, make_project, make_user):
        """哈希长度为 64（SHA-256 十六进制）"""
        from apps.files.models import FileAsset
        upload = SimpleUploadedFile('test.txt', b'some content', content_type='text/plain')
        asset = FileAsset.objects.create(
            project=make_project(), name='test.txt', file=upload, uploader=make_user(),
        )
        assert len(asset.file_hash) == 64

    def test_hash_recomputed_on_version_upload(self, teacher_client, make_project, make_user):
        """上传新版本后哈希重新计算"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        original = SimpleUploadedFile('v1.txt', b'version 1 content', content_type='text/plain')
        asset = FileAsset.objects.create(
            project=project, name='v1.txt', file=original,
            level='public', uploader=teacher_client.user,
        )
        old_hash = asset.file_hash
        assert old_hash != ''
        # 上传新版本
        new_file = SimpleUploadedFile('v2.txt', b'version 2 different content',
                                       content_type='text/plain')
        resp = teacher_client.post(
            f'/api/v1/files/{asset.id}/upload-version/',
            {'file': new_file}, format='multipart',
        )
        assert resp.status_code == 200, resp.json()
        asset.refresh_from_db()
        assert asset.file_hash != old_hash
        assert asset.file_hash != ''

    def test_hash_default_empty(self, make_project, make_user):
        """哈希字段默认为空"""
        from apps.files.models import FileAsset
        # 直接使用虚拟路径创建
        asset = FileAsset.objects.create(
            project=make_project(), name='default.txt',
            file='nonexist/file.txt', uploader=make_user(),
        )
        assert asset.file_hash == ''

    def test_image_hash_computed(self, make_project, make_user):
        """图片文件哈希正常计算"""
        from apps.files.models import FileAsset
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('test.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=make_project(), name='test.png', file=upload, uploader=make_user(),
        )
        expected = hashlib.sha256(img_bytes).hexdigest()
        assert asset.file_hash == expected


@pytest.mark.api
@pytest.mark.django_db
class TestCheckDuplicateAPI:
    """文件查重 API 测试"""

    def test_check_duplicate_finds_match(self, teacher_client, make_project, make_user):
        """查重发现重复文件"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        content = b'duplicate content here'
        a1 = FileAsset.objects.create(
            project=project, name='file1.txt',
            file=SimpleUploadedFile('file1.txt', content), uploader=teacher_client.user,
        )
        a2 = FileAsset.objects.create(
            project=project, name='file2.txt',
            file=SimpleUploadedFile('file2.txt', content), uploader=make_user(),
        )
        resp = teacher_client.get(f'/api/v1/files/{a1.id}/check-duplicate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['has_duplicate'] is True
        assert data['count'] == 1
        dup_ids = [d['id'] for d in data['duplicates']]
        assert a2.id in dup_ids

    def test_check_duplicate_no_match(self, teacher_client, make_project, make_user):
        """查重无重复"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        a1 = FileAsset.objects.create(
            project=project, name='unique1.txt',
            file=SimpleUploadedFile('unique1.txt', b'unique content AAA'), uploader=teacher_client.user,
        )
        a2 = FileAsset.objects.create(
            project=project, name='unique2.txt',
            file=SimpleUploadedFile('unique2.txt', b'unique content BBB'), uploader=make_user(),
        )
        resp = teacher_client.get(f'/api/v1/files/{a1.id}/check-duplicate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['has_duplicate'] is False
        assert data['count'] == 0

    def test_check_duplicate_no_hash(self, teacher_client, make_file):
        """文件无哈希时查重返回无重复"""
        f = make_file(uploader=teacher_client.user)
        resp = teacher_client.get(f'/api/v1/files/{f.id}/check-duplicate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['has_duplicate'] is False
        assert data['duplicates'] == []

    def test_check_duplicate_excludes_self(self, teacher_client, make_project, make_user):
        """查重排除自身"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        content = b'self exclude test'
        a1 = FileAsset.objects.create(
            project=project, name='self.txt',
            file=SimpleUploadedFile('self.txt', content), uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{a1.id}/check-duplicate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        # 只有自身，无其他重复
        assert data['count'] == 0
        dup_ids = [d['id'] for d in data['duplicates']]
        assert a1.id not in dup_ids

    def test_check_duplicate_returns_hash(self, teacher_client, make_project, make_user):
        """查重响应包含文件哈希"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        content = b'hash in response'
        a1 = FileAsset.objects.create(
            project=project, name='hash.txt',
            file=SimpleUploadedFile('hash.txt', content), uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{a1.id}/check-duplicate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['file_hash'] == a1.file_hash
        assert len(data['file_hash']) == 64

    def test_hash_in_serializer_response(self, teacher_client, make_project, make_user):
        """序列化器响应包含 file_hash 字段"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        upload = SimpleUploadedFile('serial.txt', b'serializer test', content_type='text/plain')
        asset = FileAsset.objects.create(
            project=project, name='serial.txt', file=upload, uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{asset.id}/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'file_hash' in data
        assert data['file_hash'] == asset.file_hash

    def test_watermark_text_in_serializer(self, teacher_client, make_file):
        """序列化器响应包含 watermark_text 字段"""
        f = make_file(uploader=teacher_client.user)
        f.watermark_text = '机密'
        f.save(update_fields=['watermark_text'])
        resp = teacher_client.get(f'/api/v1/files/{f.id}/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'watermark_text' in data
        assert data['watermark_text'] == '机密'
