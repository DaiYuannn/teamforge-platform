"""
导出视图
统一导出入口 ExportView
GET /api/v1/exports/?type=<导出类型>&format=<xlsx|docx|pdf>&project_id=<项目ID>
导出接口直接返回文件流（非统一 JSON 响应）
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.views import APIView

from common.permissions import IsInternalTeamMember
from common.project_access import user_can_access_project
from common.response import error_response
from .services import ExcelExportService, CsvExportService
from .word_service import WordExportService
from .pdf_service import PdfExportService


# 导入模板表头映射（type -> 表头列表）
_TEMPLATE_HEADERS = {
    'projects': ['项目名称', '项目编号', '负责人邮箱', '当前阶段', '状态', '开始时间', '预计结束'],
    'history_projects': [
        '项目名称', '项目编号', '负责人邮箱', '负责人ID', '当前阶段', '状态',
        '开始时间', '预计结束', '实际结束', '简介', '优先级',
    ],
    'members': [
        '姓名', '邮箱', '手机号', '学校', '年级', '专业', '角色',
        '成员状态', '加入团队日期', '加入小团队编号',
    ],
    'competitions': ['比赛名称', '项目编号', '级别', '主办单位', '报名日期', '答辩日期', '结果日期', '状态'],
    'finance': ['支出标题', '金额', '项目编号', '支出日期', '类别', '用途', '经办人邮箱'],
    'finance_budget': ['项目编号', '奖金总额', '其他收入', '统计周期'],
    'tasks': ['任务标题', '项目编号', '指派人邮箱', '截止时间', '开始时间', '状态', '优先级', '描述'],
    'contributions': ['项目编号', '贡献人', '贡献类型', '贡献内容', '权重', '统计周期'],
    'ip_applications': ['成果名称', '内部编号', '成果类型', '关联项目编号', '主导撰写人'],
}


class ExportTemplateView(APIView):
    """
    下载导入模板视图
    GET /api/v1/exports/template/?type=<模板类型>
    返回仅含表头的空白 Excel 模板
    """
    permission_classes = [IsInternalTeamMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=list(_TEMPLATE_HEADERS),
                required=True,
            ),
        ],
        responses={
            (
                200,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='Empty XLSX import template with the selected headers.',
            ),
        },
    )
    def get(self, request):
        import io
        import openpyxl
        from django.http import HttpResponse

        template_type = request.query_params.get('type')
        if not template_type:
            return error_response(message='请提供 type 参数指定模板类型', code=1001)

        headers = _TEMPLATE_HEADERS.get(template_type)
        if not headers:
            return error_response(message=f'不支持的模板类型：{template_type}', code=1001)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '导入模板'
        ws.append(headers)
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''导入模板_{template_type}.xlsx"
        return response


class ExportView(APIView):
    """
    统一导出视图
    - 参数 type: 导出类型
    - 参数 file_format: 格式（xlsx/docx/pdf），默认 xlsx
    - 参数 project_id: 项目ID（部分导出类型需要）
    - 参数 ip_id: 知识产权ID（IP报告导出需要）
    注意：使用 file_format 而非 format，避免与 DRF 内容协商的 format 参数冲突
    """
    permission_classes = [IsInternalTeamMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                enum=[
                    'projects', 'finance_budget', 'finance_detail', 'tasks',
                    'contributions', 'ip_applications', 'members',
                    'competitions', 'project_report', 'ip_report',
                    'finance_report',
                ],
            ),
            OpenApiParameter(
                name='file_format',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['xlsx', 'csv', 'docx', 'pdf'],
                default='xlsx',
            ),
            OpenApiParameter(
                name='project_id', type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='ip_id', type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='search', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='status', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='priority', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='assignee', type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='scope', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name='level', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY, required=False,
            ),
        ],
        responses={
            (
                200,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ): OpenApiResponse(response=OpenApiTypes.BINARY, description='XLSX export.'),
            (200, 'text/csv'): OpenApiResponse(
                response=OpenApiTypes.BINARY, description='UTF-8 CSV export.',
            ),
            (
                200,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ): OpenApiResponse(response=OpenApiTypes.BINARY, description='DOCX export.'),
            (200, 'application/pdf'): OpenApiResponse(
                response=OpenApiTypes.BINARY, description='PDF export.',
            ),
            (200, 'text/html'): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='Download fallback when the PDF renderer is unavailable.',
            ),
        },
    )
    def get(self, request):
        export_type = request.query_params.get('type')
        fmt = request.query_params.get('file_format', 'xlsx').lower()
        project_id = request.query_params.get('project_id')
        ip_id = request.query_params.get('ip_id')
        task_filters = {
            key: request.query_params.get(key)
            for key in ('search', 'status', 'priority', 'assignee', 'scope')
            if request.query_params.get(key) not in (None, '')
        }

        if not export_type:
            return error_response(message='请提供 type 参数指定导出类型', code=1001)

        project = None
        if project_id not in (None, ''):
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                return error_response(message='project_id 必须是整数', code=1001)
            from apps.projects.models import Project

            project = Project.objects.filter(pk=project_id).first()
            if project is None or not user_can_access_project(
                request.user,
                project,
            ):
                return error_response(message='项目不存在或无权导出', code=1004)

        if ip_id not in (None, ''):
            try:
                ip_id = int(ip_id)
            except (TypeError, ValueError):
                return error_response(message='ip_id 必须是整数', code=1001)
            from apps.intellectual_property.permissions import (
                accessible_ip_applications,
            )

            if not accessible_ip_applications(request.user).filter(pk=ip_id).exists():
                return error_response(message='知识产权档案不存在或无权导出', code=1004)

        try:
            # ============ Excel 导出 ============
            if fmt == 'xlsx':
                if export_type == 'projects':
                    return ExcelExportService.export_projects(user=request.user)
                elif export_type == 'finance_budget':
                    return ExcelExportService.export_finance_budget(user=request.user)
                elif export_type == 'finance_detail':
                    if not project_id:
                        return error_response(message='经费明细导出需提供 project_id', code=1001)
                    return ExcelExportService.export_finance_detail(
                        project_id,
                        user=request.user,
                    )
                elif export_type == 'tasks':
                    return ExcelExportService.export_tasks(
                        project_id,
                        filters=task_filters,
                        user=request.user,
                    )
                elif export_type == 'contributions':
                    if not project_id:
                        return error_response(message='贡献记录导出需提供 project_id', code=1001)
                    return ExcelExportService.export_contributions(
                        project_id,
                        user=request.user,
                    )
                elif export_type == 'ip_applications':
                    return ExcelExportService.export_ip_applications(user=request.user)
                elif export_type == 'members':
                    return ExcelExportService.export_members(user=request.user)
                elif export_type == 'competitions':
                    return ExcelExportService.export_competitions(
                        search=request.query_params.get('search', ''),
                        level=request.query_params.get('level', ''),
                        status=request.query_params.get('status', ''),
                        project_id=project_id,
                        user=request.user,
                    )

            # ============ Word 导出 ============
            elif fmt == 'docx':
                if export_type == 'project_report':
                    if not project_id:
                        return error_response(message='项目报告导出需提供 project_id', code=1001)
                    return WordExportService.export_project_report(project_id)
                elif export_type == 'ip_report':
                    if not ip_id:
                        return error_response(message='知识产权报告导出需提供 ip_id', code=1001)
                    return WordExportService.export_ip_report(ip_id)

            # ============ PDF 导出 ============
            elif fmt == 'pdf':
                if export_type == 'project_report':
                    if not project_id:
                        return error_response(message='项目报告导出需提供 project_id', code=1001)
                    return PdfExportService.export_project_report(project_id)
                elif export_type == 'finance_report':
                    if not project_id:
                        return error_response(
                            message='经费报告导出需提供 project_id',
                            code=1001,
                        )
                    return PdfExportService.export_finance_report(project_id)

            # ============ CSV 导出 ============
            elif fmt == 'csv':
                if export_type == 'projects':
                    return CsvExportService.export_projects(user=request.user)
                elif export_type == 'finance_budget':
                    return CsvExportService.export_finance_budget(user=request.user)
                elif export_type == 'finance_detail':
                    if not project_id:
                        return error_response(message='经费明细导出需提供 project_id', code=1001)
                    return CsvExportService.export_finance_detail(
                        project_id,
                        user=request.user,
                    )
                elif export_type == 'tasks':
                    return CsvExportService.export_tasks(
                        project_id,
                        filters=task_filters,
                        user=request.user,
                    )
                elif export_type == 'contributions':
                    if not project_id:
                        return error_response(message='贡献记录导出需提供 project_id', code=1001)
                    return CsvExportService.export_contributions(
                        project_id,
                        user=request.user,
                    )
                elif export_type == 'ip_applications':
                    return CsvExportService.export_ip_applications(user=request.user)
                elif export_type == 'members':
                    return CsvExportService.export_members(user=request.user)
                elif export_type == 'competitions':
                    return CsvExportService.export_competitions(
                        search=request.query_params.get('search', ''),
                        level=request.query_params.get('level', ''),
                        status=request.query_params.get('status', ''),
                        project_id=project_id,
                        user=request.user,
                    )

            # 不支持的类型/格式组合
            return error_response(
                message=f'不支持的导出类型或格式：type={export_type}, format={fmt}',
                code=1001,
            )

        except ValueError as e:
            # 业务校验失败（如项目不存在）
            return error_response(message=str(e), code=1004)
        except RuntimeError as e:
            # PDF 依赖不可用等运行时错误
            return error_response(message=str(e), code=1005)
        except Exception as e:
            return error_response(message=f'导出失败：{e}', code=1006)
