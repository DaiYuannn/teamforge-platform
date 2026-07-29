"""Secure preview/confirm workflow for ZIP material packages."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path
import stat
import zipfile

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import Competition
from apps.files.models import FileAsset
from apps.files.permissions import user_can_manage_file_scope
from apps.files.upload_security import (
    normalized_archive_path,
    validate_material_filename,
)
from apps.projects.models import Project
from apps.sensitive.models import SensitiveData
from apps.users.models import User
from common.project_access import project_root_team_ids


MAX_ARCHIVE_FILES = 200
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SINGLE_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_COMPRESSION_RATIO = 150
PERSONAL_SENSITIVE_TYPES = {'id_card', 'bank_account', 'phone', 'address', 'signature'}


class MaterialArchiveError(ValueError):
    pass


def _validation_error_message(exc):
    detail = getattr(exc, 'detail', exc)
    if isinstance(detail, (list, tuple)) and len(detail) == 1:
        return str(detail[0])
    if isinstance(detail, dict) and len(detail) == 1:
        value = next(iter(detail.values()))
        if isinstance(value, (list, tuple)) and len(value) == 1:
            return str(value[0])
    return str(detail)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_zip_members(archive):
    files = []
    seen = set()
    total_size = 0
    for member in archive.infolist():
        normalized = normalized_archive_path(member.filename)
        key = normalized.casefold()
        if key in seen:
            raise MaterialArchiveError(f'ZIP 中存在重复路径: {normalized}')
        seen.add(key)
        unix_mode = member.external_attr >> 16
        if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
            raise MaterialArchiveError(f'ZIP 不允许包含符号链接: {normalized}')
        if member.flag_bits & 0x1:
            raise MaterialArchiveError(f'ZIP 不允许包含加密条目: {normalized}')
        if member.is_dir():
            continue
        validate_material_filename(normalized)
        if member.file_size > MAX_SINGLE_FILE_BYTES:
            raise MaterialArchiveError(f'单个资料超过 25 MB: {normalized}')
        total_size += member.file_size
        if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise MaterialArchiveError('ZIP 解压后总大小不能超过 250 MB')
        if member.file_size and member.compress_size == 0:
            raise MaterialArchiveError(f'ZIP 条目压缩信息异常: {normalized}')
        if member.compress_size and member.file_size / member.compress_size > MAX_COMPRESSION_RATIO:
            raise MaterialArchiveError(f'ZIP 条目压缩比过高: {normalized}')
        files.append((normalized, member))
    if len(files) > MAX_ARCHIVE_FILES + 1:
        raise MaterialArchiveError(f'ZIP 最多包含 {MAX_ARCHIVE_FILES} 个资料文件')
    return files


def _load_manifest(archive, members):
    member_map = {name.casefold(): member for name, member in members}
    manifest_member = member_map.get('manifest.json')
    if manifest_member is None:
        raise MaterialArchiveError('ZIP 根目录必须包含 manifest.json')
    if manifest_member.file_size > MAX_MANIFEST_BYTES:
        raise MaterialArchiveError('manifest.json 不能超过 1 MB')
    try:
        payload = json.loads(archive.read(manifest_member).decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterialArchiveError(f'manifest.json 不是有效 UTF-8 JSON: {exc}') from exc
    if not isinstance(payload, dict) or payload.get('version') != 1:
        raise MaterialArchiveError('manifest.json 必须是 version=1 的对象')
    items = payload.get('items')
    if not isinstance(items, list) or not items:
        raise MaterialArchiveError('manifest.json.items 必须是非空数组')
    if len(items) > MAX_ARCHIVE_FILES:
        raise MaterialArchiveError(f'清单最多包含 {MAX_ARCHIVE_FILES} 项资料')
    declared = []
    for item in items:
        if not isinstance(item, dict):
            raise MaterialArchiveError('清单中的每一项都必须是对象')
        declared.append(normalized_archive_path(item.get('path', '')).casefold())
    if len(set(declared)) != len(declared):
        raise MaterialArchiveError('清单中存在重复资料路径')
    actual = {name.casefold() for name, _ in members if name.casefold() != 'manifest.json'}
    declared_set = set(declared)
    missing = declared_set - actual
    extra = actual - declared_set
    if missing:
        raise MaterialArchiveError(f'清单文件不存在: {sorted(missing)[0]}')
    if extra:
        raise MaterialArchiveError(f'ZIP 存在未列入清单的文件: {sorted(extra)[0]}')
    return items, member_map


def _resolve_project(item):
    project_id = item.get('project_id')
    project_code = str(item.get('project_code') or '').strip()
    queryset = Project.objects.all()
    if project_id:
        return queryset.filter(pk=project_id).first()
    if project_code:
        return queryset.filter(code=project_code).first()
    return None


def _resolve_team(item, default_team):
    team_id = item.get('team_id')
    team_code = str(item.get('team_code') or '').strip()
    if team_id:
        return Team.objects.filter(pk=team_id).select_related('parent').first()
    if team_code:
        return Team.objects.filter(code=team_code).select_related('parent').first()
    return default_team


def _team_root_id(team):
    return (team.parent_id or team.id) if team else None


def _validate_item(item, *, default_team, operator):
    errors = []
    try:
        path = validate_material_filename(item.get('path', ''))
    except Exception as exc:
        return None, [str(exc)]
    project = _resolve_project(item)
    if project is None:
        errors.append('必须提供有效的 project_id 或 project_code')
    level = str(item.get('level') or 'internal').strip().lower()
    if level not in {'public', 'internal', 'sensitive'}:
        errors.append('level 只能是 public、internal 或 sensitive')
    visibility = str(item.get('visibility') or ('team' if level == 'sensitive' else 'project')).strip().lower()
    if visibility not in {'project', 'team', 'competition'}:
        errors.append('visibility 只能是 project、team 或 competition')
    if level == 'public' and visibility != 'project':
        errors.append('public 资料不能指定小团队或比赛条目')

    target_team = _resolve_team(item, default_team) if visibility == 'team' or level == 'sensitive' else None
    competition = None
    if visibility == 'competition':
        competition = Competition.objects.filter(pk=item.get('competition_entry_id')).select_related(
            'project', 'event',
        ).first()
        if competition is None:
            errors.append('visibility=competition 时必须提供有效 competition_entry_id')
        elif project and competition.project_id != project.id:
            errors.append('比赛参赛条目与所选项目不一致')
    if visibility == 'team' and target_team is None:
        errors.append('visibility=team 时必须提供有效 team_id 或 team_code')

    selected_root_id = _team_root_id(default_team)
    if target_team and selected_root_id and _team_root_id(target_team) != selected_root_id:
        errors.append('资料团队不属于本次导入选择的总团队')
    if project and selected_root_id:
        roots = project_root_team_ids(project)
        if roots and selected_root_id not in roots:
            errors.append('项目不属于本次导入选择的总团队')
    if target_team and project:
        project_roots = project_root_team_ids(project)
        if project_roots and _team_root_id(target_team) not in project_roots:
            errors.append('资料团队与项目关联范围不一致')

    file_scope_team = target_team if visibility == 'team' else None
    if project and not user_can_manage_file_scope(
        operator,
        project=project,
        team=file_scope_team,
        competition_entry=competition,
    ):
        errors.append('当前用户无权向所选项目/团队/比赛范围导入资料')

    subject = None
    data_type = str(item.get('data_type') or 'other').strip().lower()
    if level == 'sensitive':
        if data_type not in dict(SensitiveData.DataType.choices):
            errors.append('敏感资料 data_type 无效')
        subject_email = str(item.get('subject_email') or '').strip()
        if subject_email:
            subject = User.objects.filter(email__iexact=subject_email, is_active=True).first()
            if subject is None:
                errors.append('subject_email 对应成员不存在')
        if data_type in PERSONAL_SENSITIVE_TYPES and subject is None:
            errors.append('个人敏感资料必须提供有效 subject_email')
        if subject and target_team and not TeamMember.objects.filter(
            team=target_team,
            user=subject,
            status=TeamMember.Status.ACTIVE,
        ).exists():
            errors.append('资料本人不是所选团队的活动成员')
        if target_team is None:
            errors.append('敏感资料必须具有所属团队')

    if errors:
        return None, errors
    return {
        'path': path,
        'name': str(item.get('name') or Path(path).name)[:255],
        'title': str(item.get('title') or item.get('name') or Path(path).name)[:200],
        'level': level,
        'visibility': visibility,
        'project_id': project.id,
        'project_name': project.name,
        'team_id': target_team.id if target_team else None,
        'team_name': target_team.name if target_team else '',
        'competition_entry_id': competition.id if competition else None,
        'competition_entry_name': (
            competition.entry_name or competition.name if competition else ''
        ),
        'data_type': data_type if level == 'sensitive' else '',
        'subject_user_id': subject.id if subject else None,
        'subject_name': subject.name if subject else '',
    }, []


def preview_material_archive(file_path, *, team, operator):
    try:
        with zipfile.ZipFile(file_path, 'r') as archive:
            members = _safe_zip_members(archive)
            items, _ = _load_manifest(archive, members)
            rows = []
            errors = {}
            for index, item in enumerate(items, start=1):
                row, row_errors = _validate_item(
                    item,
                    default_team=team,
                    operator=operator,
                )
                if row_errors:
                    errors[str(index)] = row_errors
                    rows.append({
                        'row_index': index,
                        'path': item.get('path', ''),
                        'valid': False,
                        'errors': row_errors,
                    })
                else:
                    rows.append({'row_index': index, 'valid': True, **row})
    except DRFValidationError as exc:
        # Normalize shared filename/path validation into our archive error so
        # the API can delete the staged ZIP before returning a safe 400.
        raise MaterialArchiveError(_validation_error_message(exc)) from exc
    except (zipfile.BadZipFile, zipfile.LargeZipFile, MaterialArchiveError, OSError) as exc:
        raise MaterialArchiveError(str(exc)) from exc
    return {
        'archive_sha256': _sha256_file(file_path),
        'rows': rows,
        'errors': errors,
        'total_rows': len(rows),
        'valid_rows': len(rows) - len(errors),
        'error_rows': len(errors),
    }


@transaction.atomic
def confirm_material_archive(import_task, *, operator):
    preview = preview_material_archive(
        import_task.file_path,
        team=import_task.team,
        operator=operator,
    )
    expected_hash = (import_task.preview_data or {}).get('archive_sha256')
    if not expected_hash or preview['archive_sha256'] != expected_hash:
        raise MaterialArchiveError('资料包自预览后已发生变化，请重新上传')
    if preview['error_rows']:
        raise MaterialArchiveError('资料包仍有校验错误，不能确认导入')

    created_file_ids = []
    created_sensitive_ids = []
    member_map = {}
    with zipfile.ZipFile(import_task.file_path, 'r') as archive:
        for normalized, member in _safe_zip_members(archive):
            member_map[normalized.casefold()] = member
        for row in preview['rows']:
            member = member_map[row['path'].casefold()]
            payload = archive.read(member)
            project = Project.objects.get(pk=row['project_id'])
            target_team = Team.objects.filter(pk=row['team_id']).first()
            competition = Competition.objects.filter(pk=row['competition_entry_id']).first()
            file_asset = FileAsset(
                project=project,
                team=target_team if row['visibility'] == 'team' else None,
                competition_entry=competition,
                name=row['name'],
                file=ContentFile(payload, name=Path(row['path']).name),
                level=(
                    FileAsset.Level.SENSITIVE
                    if row['level'] == 'sensitive'
                    else row['level']
                ),
                size=len(payload),
                content_type=mimetypes.guess_type(row['path'])[0] or '',
                uploader=operator,
            )
            file_asset.full_clean()
            file_asset.save()
            created_file_ids.append(file_asset.id)
            if row['level'] == 'sensitive':
                sensitive = SensitiveData.objects.create(
                    data_type=row['data_type'],
                    title=row['title'],
                    display_name=row['title'][:100],
                    encrypted_content='',
                    is_encrypted=False,
                    key_version=1,
                    file_attachment=file_asset,
                    project=project,
                    team=target_team,
                    subject_user_id=row['subject_user_id'],
                    uploader=operator,
                )
                created_sensitive_ids.append(sensitive.id)

    import_task.status = import_task.Status.CONFIRMED
    import_task.snapshot = {
        'file_ids': created_file_ids,
        'sensitive_data_ids': created_sensitive_ids,
    }
    import_task.valid_rows = len(created_file_ids)
    import_task.error_rows = 0
    import_task.error_details = {}
    import_task.save(update_fields=[
        'status', 'snapshot', 'valid_rows', 'error_rows', 'error_details', 'updated_at',
    ])
    return {
        'created_count': len(created_file_ids),
        'sensitive_count': len(created_sensitive_ids),
        'ordinary_count': len(created_file_ids) - len(created_sensitive_ids),
        'error_count': 0,
    }


@transaction.atomic
def rollback_material_archive(import_task):
    snapshot = import_task.snapshot if isinstance(import_task.snapshot, dict) else {}
    sensitive_ids = snapshot.get('sensitive_data_ids', [])
    file_ids = snapshot.get('file_ids', [])
    SensitiveData.objects.filter(pk__in=sensitive_ids).delete()
    files = list(FileAsset.all_objects.filter(pk__in=file_ids))
    for file_asset in files:
        if file_asset.file:
            file_asset.file.delete(save=False)
    FileAsset.all_objects.filter(pk__in=file_ids).delete()
    import_task.status = import_task.Status.ROLLED_BACK
    import_task.save(update_fields=['status', 'updated_at'])
    return f'已回滚 {len(file_ids)} 个资料文件'
