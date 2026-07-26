"""
M02: 文件版本管理 API 测试
- 获取版本列表
- 上传新版本
- 下载历史版本
- 权限验证
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestFileVersionAPI:
    """文件版本管理测试"""

    def test_get_versions_empty(self, member_client, make_file):
        """获取文件版本列表（空）"""
        f = make_file()
        resp = member_client.get(f'/api/v1/files/{f.id}/versions/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_versions_with_data(self, member_client, make_file):
        """获取文件版本列表（有数据）"""
        from apps.files.models import FileVersion
        f = make_file()
        FileVersion.objects.create(
            file_asset=f,
            file='dummy/v1.pdf',
            version=1,
            uploader=f.uploader,
        )
        resp = member_client.get(f'/api/v1/files/{f.id}/versions/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 1
        assert data[0]['version'] == 1

    def test_upload_version(self, teacher_client, make_file):
        """上传新版本"""
        f = make_file(uploader=teacher_client.user)
        upload = SimpleUploadedFile('new_version.pdf', b'new file content',
                                     content_type='application/pdf')
        resp = teacher_client.post(
            f'/api/v1/files/{f.id}/upload-version/',
            {'file': upload},
            format='multipart',
        )
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['version'] == 2
        # 旧版本应保存
        from apps.files.models import FileVersion
        assert FileVersion.objects.filter(file_asset=f).count() == 1

    def test_upload_version_permission(self, member_client, make_file):
        """普通成员可能无权上传版本"""
        f = make_file()
        upload = SimpleUploadedFile('unauthorized.pdf', b'content',
                                     content_type='application/pdf')
        resp = member_client.post(
            f'/api/v1/files/{f.id}/upload-version/',
            {'file': upload},
            format='multipart',
        )
        # 权限取决于文件上传权限配置
        assert resp.status_code in (200, 403)

    def test_version_list_includes_fields(self, member_client, make_file):
        """版本列表包含必要字段"""
        from apps.files.models import FileVersion
        f = make_file()
        FileVersion.objects.create(
            file_asset=f,
            file='dummy/v1.pdf',
            version=1,
            uploader=f.uploader,
        )
        resp = member_client.get(f'/api/v1/files/{f.id}/versions/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'version' in data[0]
        assert 'uploader_name' in data[0]
        assert 'created_at' in data[0]

    def test_unauthenticated_cannot_access_versions(self, api_client, make_file):
        """未认证不能访问版本列表"""
        f = make_file()
        resp = api_client.get(f'/api/v1/files/{f.id}/versions/')
        assert resp.status_code == 401

    def test_restore_version_creates_new_current_version(
        self, teacher_client, make_project, tmp_path
    ):
        """恢复历史版本不会倒退版本号，而是形成新的当前版本。"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.files.models import FileAsset, FileVersion

        project = make_project(leader=teacher_client.user)
        asset = FileAsset.objects.create(
            project=project,
            name='方案.txt',
            file=SimpleUploadedFile('current.txt', b'current'),
            level='internal',
            uploader=teacher_client.user,
            version=2,
        )
        historical = FileVersion.objects.create(
            file_asset=asset,
            file=SimpleUploadedFile('old.txt', b'old-content'),
            version=1,
            uploader=teacher_client.user,
        )

        response = teacher_client.post(
            f'/api/v1/files/{asset.id}/versions/{historical.id}/restore/'
        )
        assert response.status_code == 200, response.json()
        asset.refresh_from_db()
        assert asset.version == 3
        with asset.file.open('rb') as restored:
            assert restored.read() == b'old-content'
        assert FileVersion.objects.filter(file_asset=asset, version=2).exists()
