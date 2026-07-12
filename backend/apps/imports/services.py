"""
数据导入业务逻辑服务
导入流程: preview(上传+解析+字段映射+返回预览) -> confirm(事务写入) -> rollback(根据快照回滚)
使用 openpyxl 解析 Excel 文件，pandas 辅助数据处理
"""
import os
import json
from decimal import Decimal
from django.db import transaction
from django.conf import settings

from .models import ImportTask


class ImportService:
    """数据导入服务"""

    # 各模块对应的模型类和必填字段
    MODULE_CONFIG = {
        'projects': {
            'model': 'apps.projects.models.Project',
            'required_fields': ['name', 'code'],
            'optional_fields': ['intro', 'priority', 'status', 'start_date', 'planned_end_date'],
        },
        'history_projects': {
            # 历史项目导入：导入已结项/归档的历史项目数据
            # 额外支持字段：actual_end_date（实际结束日期）、current_stage（当前阶段）
            # 默认 status=closed（已关闭/已结项）
            'model': 'apps.projects.models.Project',
            'required_fields': ['name', 'code'],
            'optional_fields': [
                'intro', 'priority', 'status', 'start_date', 'planned_end_date',
                'actual_end_date', 'current_stage', 'leader_id',
            ],
            'defaults': {'status': 'closed'},
        },
        'members': {
            'model': 'apps.users.models.User',
            'required_fields': ['name', 'email'],
            'optional_fields': ['phone', 'grade', 'major', 'global_role', 'is_student'],
        },
        'competitions': {
            'model': 'apps.competitions.models.Competition',
            'required_fields': ['name', 'project'],
            'optional_fields': ['level', 'organizer', 'status', 'register_date'],
        },
        'tasks': {
            'model': 'apps.tasks.models.Task',
            'required_fields': ['title', 'project', 'assignee'],
            'optional_fields': ['description', 'deadline', 'status'],
        },
        'finance': {
            'model': 'apps.finance.models.FinanceExpense',
            'required_fields': ['title', 'amount', 'project', 'expense_date'],
            'optional_fields': ['category', 'purpose', 'spender'],
        },
        'ip_applications': {
            'model': 'apps.intellectual_property.models.IntellectualPropertyApplication',
            'required_fields': ['title', 'application_code'],
            'optional_fields': ['ip_type', 'related_project', 'status', 'main_writer', 'intro'],
        },
    }

    @staticmethod
    def parse_excel(file_path):
        """
        使用 openpyxl + pandas 解析 Excel 文件
        :param file_path: 文件路径
        :return: (headers, rows) 表头和数据行列表
        """
        import pandas as pd

        # 读取 Excel 文件
        df = pd.read_excel(file_path, engine='openpyxl')
        # 获取表头
        headers = df.columns.tolist()
        # 转换数据为字典列表（处理 NaN）
        rows = df.fillna('').to_dict('records')
        # 将所有值转为字符串（除数值外）
        for row in rows:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
                elif isinstance(value, float) and value.is_integer():
                    row[key] = int(value)
                else:
                    row[key] = str(value) if value != '' else ''
        return headers, rows

    @staticmethod
    def auto_map_fields(headers, module):
        """
        自动字段映射：根据表头和模块配置，尝试自动匹配字段
        :param headers: Excel 表头列表
        :param module: 导入模块
        :return: 字段映射字典 {源列名: 目标字段名}
        """
        config = ImportService.MODULE_CONFIG.get(module, {})
        all_fields = config.get('required_fields', []) + config.get('optional_fields', [])

        mapping = {}
        for header in headers:
            header_lower = str(header).lower().strip()
            # 精确匹配
            if header_lower in all_fields:
                mapping[header] = header_lower
            # 模糊匹配（中文列名映射）
            else:
                # 预定义中文映射表
                cn_mapping = {
                    '项目名称': 'name', '名称': 'name', '标题': 'title',
                    '项目编号': 'code', '编号': 'code',
                    '负责人': 'leader', '指派人': 'assignee', '经办人': 'spender',
                    '邮箱': 'email', '手机': 'phone', '手机号': 'phone',
                    '年级': 'grade', '专业': 'major', '角色': 'global_role',
                    '简介': 'intro', '描述': 'description',
                    '金额': 'amount', '日期': 'expense_date', '支出日期': 'expense_date',
                    '类别': 'category', '用途': 'purpose',
                    '优先级': 'priority', '状态': 'status',
                    '开始日期': 'start_date', '计划结束日期': 'planned_end_date',
                    '预计结束': 'planned_end_date', '开始时间': 'start_date',
                    # 历史项目相关
                    '实际结束日期': 'actual_end_date', '实际结束': 'actual_end_date',
                    '当前阶段': 'current_stage', '负责人ID': 'leader_id',
                    '截止时间': 'deadline', '级别': 'level', '主办单位': 'organizer',
                    # 知识产权相关
                    '成果名称': 'title', '内部编号': 'application_code',
                    '成果类型': 'ip_type', '关联项目': 'related_project',
                    '关联项目编号': 'related_project', '主导撰写人': 'main_writer',
                    '撰写人': 'main_writer',
                }
                if header in cn_mapping and cn_mapping[header] in all_fields:
                    mapping[header] = cn_mapping[header]

        return mapping

    @staticmethod
    def validate_rows(rows, field_mapping, module):
        """
        校验数据行
        :param rows: 数据行列表
        :param field_mapping: 字段映射
        :param module: 导入模块
        :return: (valid_rows, error_details)
        """
        config = ImportService.MODULE_CONFIG.get(module, {})
        required_fields = config.get('required_fields', [])

        valid_rows = []
        error_details = {}

        # 获取映射后的必填字段对应的源列名
        required_source_columns = []
        for source_col, target_field in field_mapping.items():
            if target_field in required_fields:
                required_source_columns.append(source_col)

        for idx, row in enumerate(rows, start=1):
            errors = []
            # 检查必填字段
            for req_col in required_source_columns:
                value = row.get(req_col, '')
                if not value or value == '':
                    errors.append(f'必填字段 "{req_col}" 为空')

            if errors:
                error_details[idx] = errors
            else:
                # 将源数据映射为目标字段格式
                mapped_row = {}
                for source_col, target_field in field_mapping.items():
                    mapped_row[target_field] = row.get(source_col, '')
                valid_rows.append(mapped_row)

        return valid_rows, error_details

    @staticmethod
    @transaction.atomic
    def confirm_import(import_task, field_mapping=None):
        """
        确认导入：将预览数据写入数据库
        :param import_task: 导入任务实例
        :param field_mapping: 最终字段映射
        :return: (success, result)
        """
        if field_mapping:
            import_task.field_mapping = field_mapping
            import_task.save()

        # 使用更新后的字段映射重新校验
        headers, rows = ImportService.parse_excel(import_task.file_path)
        if not field_mapping:
            field_mapping = import_task.field_mapping

        valid_rows, error_details = ImportService.validate_rows(
            rows, field_mapping, import_task.module
        )

        if not valid_rows:
            import_task.status = ImportTask.Status.FAILED
            import_task.error_details = {'message': '没有有效数据可导入'}
            import_task.save()
            return False, '没有有效数据可导入'

        # 获取目标模型类
        config = ImportService.MODULE_CONFIG.get(import_task.module, {})
        model_path = config.get('model', '')
        parts = model_path.rsplit('.', 1)
        if len(parts) != 2:
            return False, '模块配置错误'
        module_name, class_name = parts
        import importlib
        mod = importlib.import_module(module_name)
        ModelClass = getattr(mod, class_name)

        # 模块级默认值（如历史项目导入默认 status=closed）
        defaults = config.get('defaults', {})

        # 写入数据并记录快照
        created_ids = []
        for row_data in valid_rows:
            try:
                # 过滤空值
                clean_data = {k: v for k, v in row_data.items() if v != '' and v is not None}
                # 应用模块级默认值：仅当字段未提供或为空时填充
                for field, default_value in defaults.items():
                    if not clean_data.get(field):
                        clean_data[field] = default_value
                obj = ModelClass.objects.create(**clean_data)
                created_ids.append(obj.id)
            except Exception as e:
                if not import_task.error_details:
                    import_task.error_details = {}
                import_task.error_details[f'row_{len(created_ids) + 1}'] = str(e)

        # 更新任务状态
        import_task.status = ImportTask.Status.CONFIRMED
        import_task.snapshot = created_ids
        import_task.valid_rows = len(created_ids)
        import_task.error_rows = len(valid_rows) - len(created_ids)
        import_task.save()

        return True, {
            'created_count': len(created_ids),
            'error_count': len(valid_rows) - len(created_ids),
        }

    @staticmethod
    @transaction.atomic
    def rollback_import(import_task):
        """
        回滚导入：根据快照删除已写入的数据
        :param import_task: 导入任务实例
        :return: (success, message)
        """
        if import_task.status != ImportTask.Status.CONFIRMED:
            return False, '只有已确认的导入任务可以回滚'

        snapshot = import_task.snapshot or []
        if not snapshot:
            return False, '没有可回滚的数据'

        # 获取目标模型类
        config = ImportService.MODULE_CONFIG.get(import_task.module, {})
        model_path = config.get('model', '')
        parts = model_path.rsplit('.', 1)
        if len(parts) != 2:
            return False, '模块配置错误'
        module_name, class_name = parts
        import importlib
        mod = importlib.import_module(module_name)
        ModelClass = getattr(mod, class_name)

        # 删除已写入的数据
        deleted_count, _ = ModelClass.objects.filter(id__in=snapshot).delete()

        # 更新任务状态
        import_task.status = ImportTask.Status.ROLLED_BACK
        import_task.save()

        return True, f'已回滚 {deleted_count} 条数据'


# 全局服务实例
import_service = ImportService()
