"""数据导入服务。

导入流程为 preview -> confirm -> rollback。跨表关系优先使用项目编号和成员
邮箱等稳定标识，仍兼容旧模板中的数字 ID。
"""
from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import ImportTask


class ImportService:
    """负责导入文件解析、字段映射、校验、写入和回滚。"""

    MODULE_CONFIG = {
        'projects': {
            'model': 'apps.projects.models.Project',
            'required_fields': ['name', 'code'],
            'optional_fields': [
                'leader_email', 'leader_id', 'intro', 'priority', 'status',
                'current_stage', 'start_date', 'planned_end_date',
            ],
        },
        'history_projects': {
            'model': 'apps.projects.models.Project',
            'required_fields': ['name', 'code'],
            'optional_fields': [
                'leader_email', 'leader_id', 'intro', 'priority', 'status',
                'start_date', 'planned_end_date', 'actual_end_date', 'current_stage',
            ],
            'defaults': {'status': 'closed', 'current_stage': 14},
        },
        'members': {
            'model': 'apps.users.models.User',
            'required_fields': ['name', 'email'],
            'optional_fields': [
                'phone', 'school', 'grade', 'major', 'global_role', 'is_student',
                'membership_status', 'team_joined_at', 'target_team_code',
            ],
        },
        'competitions': {
            'model': 'apps.competitions.models.Competition',
            'required_fields': ['name', 'project_code'],
            'optional_fields': [
                'level', 'organizer', 'status', 'register_date', 'defense_date',
                'result_date', 'award_level', 'is_awarded',
            ],
        },
        'tasks': {
            'model': 'apps.tasks.models.Task',
            'required_fields': ['title', 'project_code', 'assignee_email'],
            'optional_fields': [
                'description', 'deadline', 'start_date', 'status', 'priority',
            ],
        },
        'finance': {
            'model': 'apps.finance.models.FinanceExpense',
            'required_fields': ['title', 'amount', 'project_code', 'expense_date'],
            'optional_fields': ['category', 'purpose', 'spender_email'],
        },
        'ip_applications': {
            'model': 'apps.intellectual_property.models.IntellectualPropertyApplication',
            'required_fields': ['title', 'application_code'],
            'optional_fields': [
                'ip_type', 'related_project_code', 'status', 'main_writer_email',
                'intro', 'start_date', 'authorized_date',
            ],
        },
    }

    FIELD_LABELS = {
        'name': '名称',
        'code': '项目编号',
        'leader_email': '负责人邮箱',
        'leader_id': '负责人 ID（兼容旧模板）',
        'intro': '简介',
        'priority': '优先级',
        'status': '状态',
        'current_stage': '当前阶段',
        'start_date': '开始日期',
        'planned_end_date': '计划结束日期',
        'actual_end_date': '实际结束日期',
        'email': '邮箱',
        'phone': '手机号',
        'school': '学校',
        'grade': '年级',
        'major': '专业',
        'global_role': '全局角色',
        'is_student': '是否学生',
        'membership_status': '成员状态',
        'team_joined_at': '加入团队日期',
        'target_team_code': '加入小团队编号',
        'title': '标题',
        'project_code': '项目编号',
        'assignee_email': '负责人邮箱',
        'spender_email': '经办人邮箱',
        'related_project_code': '关联项目编号',
        'main_writer_email': '主导撰写人邮箱',
        'level': '级别',
        'organizer': '主办单位',
        'register_date': '报名日期',
        'defense_date': '答辩日期',
        'result_date': '结果日期',
        'award_level': '获奖等级',
        'is_awarded': '是否获奖',
        'description': '描述',
        'deadline': '截止时间',
        'amount': '金额',
        'expense_date': '支出日期',
        'category': '类别',
        'purpose': '用途',
        'ip_type': '成果类型',
        'application_code': '内部编号',
        'authorized_date': '授权日期',
    }

    CN_FIELD_MAP = {
        '项目名称': 'name',
        '名称': 'name',
        '成员姓名': 'name',
        '姓名': 'name',
        '比赛名称': 'name',
        '任务标题': 'title',
        '支出标题': 'title',
        '标题': 'title',
        '成果名称': 'title',
        '项目编号': 'project_code',
        '编号': 'code',
        '负责人邮箱': 'leader_email',
        '负责人ID': 'leader_id',
        '负责人 ID': 'leader_id',
        '指派人邮箱': 'assignee_email',
        '指派给': 'assignee_email',
        '经办人邮箱': 'spender_email',
        '经办人': 'spender_email',
        '邮箱': 'email',
        '手机': 'phone',
        '手机号': 'phone',
        '学校': 'school',
        '年级': 'grade',
        '专业': 'major',
        '角色': 'global_role',
        '成员状态': 'membership_status',
        '加入团队日期': 'team_joined_at',
        '加入小团队编号': 'target_team_code',
        '团队编号': 'target_team_code',
        '是否学生': 'is_student',
        '简介': 'intro',
        '描述': 'description',
        '金额': 'amount',
        '日期': 'expense_date',
        '支出日期': 'expense_date',
        '类别': 'category',
        '用途': 'purpose',
        '优先级': 'priority',
        '状态': 'status',
        '开始日期': 'start_date',
        '开始时间': 'start_date',
        '计划结束日期': 'planned_end_date',
        '预计结束': 'planned_end_date',
        '实际结束日期': 'actual_end_date',
        '实际结束': 'actual_end_date',
        '当前阶段': 'current_stage',
        '截止时间': 'deadline',
        '级别': 'level',
        '主办单位': 'organizer',
        '报名日期': 'register_date',
        '答辩日期': 'defense_date',
        '结果日期': 'result_date',
        '获奖等级': 'award_level',
        '是否获奖': 'is_awarded',
        '内部编号': 'application_code',
        '成果类型': 'ip_type',
        '关联项目': 'related_project_code',
        '关联项目编号': 'related_project_code',
        '主导撰写人': 'main_writer_email',
        '主导撰写人邮箱': 'main_writer_email',
        '撰写人': 'main_writer_email',
        '授权日期': 'authorized_date',
    }

    @classmethod
    def get_field_options(cls, module):
        config = cls.MODULE_CONFIG.get(module, {})
        required = set(config.get('required_fields', []))
        fields = config.get('required_fields', []) + config.get('optional_fields', [])
        return [
            {
                'value': field,
                'label': cls.FIELD_LABELS.get(field, field),
                'required': field in required,
            }
            for field in fields
        ]

    @staticmethod
    def parse_excel(file_path):
        """解析 xlsx 或 csv，返回表头及由普通 Python 值组成的数据行。"""
        import pandas as pd

        suffix = Path(file_path).suffix.lower()
        if suffix == '.csv':
            try:
                frame = pd.read_csv(file_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                frame = pd.read_csv(file_path, encoding='gb18030')
        elif suffix in {'.xlsx', '.xlsm'}:
            frame = pd.read_excel(file_path, engine='openpyxl')
        else:
            raise ValueError('仅支持 .xlsx、.xlsm 或 .csv 文件')

        headers = [str(column).strip() for column in frame.columns.tolist()]
        frame.columns = headers
        rows = frame.fillna('').to_dict('records')
        for row in rows:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
                elif isinstance(value, float) and value.is_integer():
                    row[key] = int(value)
                elif value != '':
                    row[key] = str(value).strip()
        return headers, rows

    @classmethod
    def auto_map_fields(cls, headers, module):
        config = cls.MODULE_CONFIG.get(module, {})
        available = set(config.get('required_fields', []) + config.get('optional_fields', []))
        mapping = {}

        for header in headers:
            normalized = str(header).strip()
            lower = normalized.lower()
            target = lower if lower in available else cls.CN_FIELD_MAP.get(normalized)

            # “项目编号”在项目模块中是项目自身 code，在关联模块中是 project_code。
            if normalized == '项目编号' and module in {'projects', 'history_projects'}:
                target = 'code'
            if normalized in {'负责人', '负责人邮箱'} and module in {'tasks'}:
                target = 'assignee_email'
            if normalized in {'负责人', '负责人邮箱'} and module in {'projects', 'history_projects'}:
                target = 'leader_email'
            if target in available:
                mapping[normalized] = target
        return mapping

    @classmethod
    def validate_rows(cls, rows, field_mapping, module):
        config = cls.MODULE_CONFIG.get(module)
        if not config:
            return [], {0: ['不支持的导入模块']}

        required_fields = config.get('required_fields', [])
        mapped_targets = set(field_mapping.values())
        missing_mappings = [field for field in required_fields if field not in mapped_targets]
        valid_rows = []
        error_details = {}

        for index, row in enumerate(rows, start=1):
            errors = []
            if missing_mappings:
                labels = '、'.join(cls.FIELD_LABELS.get(field, field) for field in missing_mappings)
                errors.append(f'缺少必填字段映射：{labels}')

            mapped_row = {
                target: row.get(source, '')
                for source, target in field_mapping.items()
                if target
            }
            for field in required_fields:
                if not mapped_row.get(field):
                    errors.append(f'必填字段“{cls.FIELD_LABELS.get(field, field)}”为空')

            if errors:
                error_details[index] = errors
            else:
                valid_rows.append(mapped_row)
        return valid_rows, error_details

    @staticmethod
    def _load_model(model_path):
        module_name, class_name = model_path.rsplit('.', 1)
        return getattr(importlib.import_module(module_name), class_name)

    @staticmethod
    def _resolve_project(value):
        from apps.projects.models import Project

        if value in (None, ''):
            return None
        project = Project.objects.filter(code__iexact=str(value).strip()).first()
        if project:
            return project
        if str(value).isdigit():
            project = Project.objects.filter(pk=int(value)).first()
        if not project:
            raise ValueError(f'未找到项目编号：{value}')
        return project

    @staticmethod
    def _resolve_user(value):
        from apps.users.models import User

        if value in (None, ''):
            return None
        text = str(value).strip()
        user = User.objects.filter(email__iexact=text).first()
        if user:
            return user
        if text.isdigit():
            user = User.objects.filter(pk=int(text)).first()
            if user:
                return user
        matches = User.objects.filter(name=text)
        if matches.count() == 1:
            return matches.first()
        if matches.count() > 1:
            raise ValueError(f'成员姓名“{text}”不唯一，请改用邮箱')
        raise ValueError(f'未找到成员邮箱：{text}')

    @staticmethod
    def _user_manages_team(user, team):
        """与团队管理接口保持一致，包含总团队负责人管理其直属小团队。"""
        if not user or not team or not getattr(user, 'is_active', False):
            return False
        if getattr(user, 'global_role', '') == 'sys_admin':
            return True

        from apps.common.team_models import TeamMember

        manager_roles = [
            TeamMember.Role.OWNER,
            TeamMember.Role.CO_LEAD,
            TeamMember.Role.ADMIN,
        ]
        if (
            team.owner_id == user.id
            or TeamMember.objects.filter(
                team=team,
                user=user,
                role__in=manager_roles,
                status=TeamMember.Status.ACTIVE,
            ).exists()
        ):
            return True
        parent = getattr(team, 'parent', None)
        return bool(
            parent
            and (
                parent.owner_id == user.id
                or TeamMember.objects.filter(
                    team=parent,
                    user=user,
                    role__in=manager_roles,
                    status=TeamMember.Status.ACTIVE,
                ).exists()
            )
        )

    @classmethod
    def _validate_import_scope(
        cls,
        clean_data,
        module,
        *,
        operator,
        default_team=None,
    ):
        """逐行校验导入权限，不能只依赖预览任务上的团队字段。"""
        from common.project_access import project_can_manage
        from apps.common.team_models import Team

        # 升级前没有 Team 数据的旧部署保留原有导入能力；一旦建立团队，
        # 所有导入立即进入下面的团队/项目范围校验。
        legacy_without_teams = (
            default_team is None
            and not Team.objects.exists()
        )
        if legacy_without_teams:
            return

        global_role = getattr(operator, 'global_role', '')
        is_platform_manager = global_role in {'sys_admin', 'teacher'}
        if module == 'members':
            if (
                not is_platform_manager
                and not cls._user_manages_team(operator, default_team)
            ):
                raise ValueError('无权向所选团队导入成员')
            return
        if module in {'projects', 'history_projects'}:
            if not is_platform_manager and not cls._user_manages_team(
                operator,
                default_team,
            ):
                raise ValueError('无权为所选团队创建项目')
            leader = clean_data.get('leader')
            if not leader or not leader.is_active or leader.membership_status == 'exited':
                raise ValueError('项目负责人必须是有效团队成员')
            if default_team and not is_platform_manager:
                from apps.common.team_models import TeamMember

                if (
                    default_team.owner_id != leader.id
                    and not TeamMember.objects.filter(
                        team=default_team,
                        user=leader,
                        status=TeamMember.Status.ACTIVE,
                    ).exists()
                ):
                    raise ValueError('项目负责人必须是目标团队的活动成员')
            return

        project = clean_data.get('project') or clean_data.get('related_project')
        if project is None:
            # 当前只有知识产权导入允许不关联项目；仍要求操作者是所选团队
            # 管理者，避免任意内部成员批量创建无归属档案。
            if (
                module != 'ip_applications'
                or (
                    not is_platform_manager
                    and not cls._user_manages_team(operator, default_team)
                )
            ):
                raise ValueError('导入记录必须关联有权管理的项目')
            return

        can_manage_project = project_can_manage(operator, project)
        can_manage_linked_team = bool(
            default_team
            and cls._user_manages_team(operator, default_team)
            and project.teams.filter(pk=default_team.pk).exists()
        )
        if not (can_manage_project or can_manage_linked_team):
            raise ValueError(f'无权向项目“{project.name}”导入数据')

        if module == 'tasks':
            from apps.projects.models import ProjectMember

            assignee = clean_data.get('assignee')
            if (
                assignee
                and assignee.id != project.leader_id
                and not ProjectMember.objects.filter(
                    project=project,
                    user=assignee,
                    status=ProjectMember.Status.ACTIVE,
                ).exists()
            ):
                raise ValueError('任务负责人必须是目标项目的活动成员')
        elif module == 'ip_applications':
            from apps.projects.models import ProjectMember

            writer = clean_data.get('main_writer')
            if (
                writer
                and writer.id != project.leader_id
                and not ProjectMember.objects.filter(
                    project=project,
                    user=writer,
                    status=ProjectMember.Status.ACTIVE,
                ).exists()
            ):
                raise ValueError('主导撰写人必须是关联项目的活动成员')

    @staticmethod
    def _to_boolean(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {'1', 'true', 'yes', 'y', '是', '已获奖'}

    @classmethod
    def _prepare_data(cls, row_data, module, created_by):
        clean = {key: value for key, value in row_data.items() if value not in ('', None)}

        if module in {'projects', 'history_projects'}:
            leader_key = clean.pop('leader_email', None) or clean.pop('leader_id', None)
            clean['leader'] = cls._resolve_user(leader_key) if leader_key else created_by
            if not clean.get('leader'):
                raise ValueError('项目负责人不能为空，请填写负责人邮箱')
            if 'current_stage' in clean:
                clean['current_stage'] = int(clean['current_stage'])
        elif module == 'competitions':
            clean['project'] = cls._resolve_project(clean.pop('project_code'))
            if 'is_awarded' in clean:
                clean['is_awarded'] = cls._to_boolean(clean['is_awarded'])
        elif module == 'tasks':
            clean['project'] = cls._resolve_project(clean.pop('project_code'))
            clean['assignee'] = cls._resolve_user(clean.pop('assignee_email'))
            clean['creator'] = created_by
            for field in ('deadline', 'start_date'):
                value = clean.get(field)
                if not isinstance(value, str):
                    continue
                parsed = parse_datetime(value)
                if parsed and timezone.is_naive(parsed):
                    parsed = timezone.make_aware(parsed)
                if parsed:
                    clean[field] = parsed
        elif module == 'finance':
            clean['project'] = cls._resolve_project(clean.pop('project_code'))
            spender = clean.pop('spender_email', None)
            clean['spender'] = cls._resolve_user(spender) if spender else created_by
        elif module == 'ip_applications':
            project_code = clean.pop('related_project_code', None)
            writer = clean.pop('main_writer_email', None)
            clean['related_project'] = cls._resolve_project(project_code) if project_code else None
            clean['main_writer'] = cls._resolve_user(writer) if writer else created_by
            clean['created_by'] = created_by
        elif module == 'members':
            if 'is_student' in clean:
                clean['is_student'] = cls._to_boolean(clean['is_student'])
        return clean

    @staticmethod
    def _unique_username(email):
        from apps.users.models import User

        local = str(email).split('@', 1)[0]
        base = re.sub(r'[^a-zA-Z0-9_.-]+', '', local)[:120] or 'member'
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f'{base[:140 - len(str(suffix))]}-{suffix}'
        return username

    @classmethod
    def _create_instance(cls, ModelClass, clean_data, module, *, default_team=None, created_by=None):
        if module == 'members':
            from apps.common.team_models import Team, TeamMember

            team_code = clean_data.pop('target_team_code', None)
            target_team = default_team
            if team_code:
                target_team = Team.objects.filter(code__iexact=str(team_code).strip()).first()
                if target_team is None:
                    raise ValueError(f'未找到小团队编号：{team_code}')
            if target_team is not None:
                can_manage = cls._user_manages_team(created_by, target_team)
                if not can_manage:
                    raise ValueError(f'无权向团队“{target_team.name}”导入成员')
            clean_data.setdefault('username', cls._unique_username(clean_data['email']))
            instance = ModelClass(**clean_data)
            instance.set_unusable_password()
            instance.save()
            if target_team is not None:
                TeamMember.objects.create(
                    team=target_team,
                    user=instance,
                    role=TeamMember.Role.MEMBER,
                )
            return instance
        if module in {'projects', 'history_projects'}:
            from apps.projects.models import (
                ProjectMember,
                ProjectMembershipEvent,
                ProjectStageLog,
            )

            instance = ModelClass.objects.create(**clean_data)
            if default_team is not None:
                instance.teams.add(default_team)
            membership, created = ProjectMember.objects.get_or_create(
                project=instance,
                user=instance.leader,
                defaults={
                    'role_in_project': ProjectMember.RoleInProject.LEADER,
                },
            )
            if created:
                ProjectMembershipEvent.objects.create(
                    membership=membership,
                    event_type=ProjectMembershipEvent.EventType.JOINED,
                    to_role=membership.role_in_project,
                    to_status=membership.status,
                    operator=created_by,
                )
            ProjectStageLog.objects.create(
                project=instance,
                from_stage=None,
                to_stage=instance.current_stage,
                operator=created_by,
                note='批量导入创建',
            )
            return instance
        if module == 'ip_applications':
            from apps.intellectual_property.models import IPApplicationProjectLink

            instance = ModelClass.objects.create(**clean_data)
            if instance.related_project_id:
                IPApplicationProjectLink.objects.get_or_create(
                    application=instance,
                    project=instance.related_project,
                    defaults={
                        'relation_type': IPApplicationProjectLink.RelationType.PRIMARY,
                    },
                )
            return instance
        return ModelClass.objects.create(**clean_data)

    @classmethod
    @transaction.atomic
    def confirm_import(cls, import_task, field_mapping=None, *, operator=None):
        if field_mapping is not None:
            import_task.field_mapping = field_mapping
            import_task.save(update_fields=['field_mapping', 'updated_at'])
        else:
            field_mapping = import_task.field_mapping

        _headers, rows = cls.parse_excel(import_task.file_path)
        valid_rows, validation_errors = cls.validate_rows(
            rows, field_mapping, import_task.module
        )
        if not valid_rows:
            import_task.status = ImportTask.Status.FAILED
            import_task.error_details = validation_errors or {'message': '没有有效数据可导入'}
            import_task.error_rows = len(rows)
            import_task.save(update_fields=['status', 'error_details', 'error_rows', 'updated_at'])
            return False, '没有有效数据可导入'

        config = cls.MODULE_CONFIG[import_task.module]
        ModelClass = cls._load_model(config['model'])
        defaults = config.get('defaults', {})
        created_ids = []
        write_errors = dict(validation_errors)
        permission_operator = operator or import_task.created_by

        for row_index, row_data in enumerate(valid_rows, start=1):
            try:
                clean_data = cls._prepare_data(
                    row_data, import_task.module, import_task.created_by
                )
                for field, value in defaults.items():
                    clean_data.setdefault(field, value)
                cls._validate_import_scope(
                    clean_data,
                    import_task.module,
                    operator=permission_operator,
                    default_team=import_task.team,
                )
                # 单行保存点避免某行唯一约束失败后破坏整批事务。
                with transaction.atomic():
                    obj = cls._create_instance(
                        ModelClass,
                        clean_data,
                        import_task.module,
                        default_team=import_task.team,
                        created_by=import_task.created_by,
                    )
                created_ids.append(obj.pk)
            except Exception as exc:
                write_errors[f'row_{row_index}'] = [str(exc)]

        import_task.snapshot = created_ids
        import_task.valid_rows = len(created_ids)
        import_task.error_rows = len(rows) - len(created_ids)
        import_task.error_details = write_errors
        import_task.status = (
            ImportTask.Status.CONFIRMED if created_ids else ImportTask.Status.FAILED
        )
        import_task.save(update_fields=[
            'snapshot', 'valid_rows', 'error_rows', 'error_details', 'status', 'updated_at',
        ])

        if not created_ids:
            return False, '所有数据写入失败，请查看错误详情'
        return True, {
            'created_count': len(created_ids),
            'error_count': len(rows) - len(created_ids),
            'errors': write_errors,
        }

    @classmethod
    @transaction.atomic
    def rollback_import(cls, import_task):
        if import_task.status != ImportTask.Status.CONFIRMED:
            return False, '只有已确认的导入任务可以回滚'
        snapshot = import_task.snapshot or []
        if not snapshot:
            return False, '没有可回滚的数据'

        config = cls.MODULE_CONFIG.get(import_task.module, {})
        ModelClass = cls._load_model(config['model'])
        deleted_count, _ = ModelClass.objects.filter(pk__in=snapshot).delete()
        import_task.status = ImportTask.Status.ROLLED_BACK
        import_task.save(update_fields=['status', 'updated_at'])
        import_root = (Path(settings.MEDIA_ROOT) / 'imports').resolve()
        file_path = Path(import_task.file_path).resolve()
        try:
            file_path.relative_to(import_root)
        except ValueError:
            # 历史/异常任务可能指向导入目录之外；回滚业务数据即可，
            # 绝不能把数据库字段当作任意本地文件删除路径。
            pass
        else:
            try:
                file_path.unlink()
            except (FileNotFoundError, OSError):
                pass
        return True, f'已回滚 {deleted_count} 条数据'


import_service = ImportService()
