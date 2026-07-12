"""
导出视图
统一导出入口 ExportView
GET /api/v1/exports/?type=<导出类型>&format=<xlsx|docx|pdf>&project_id=<项目ID>
导出接口直接返回文件流（非统一 JSON 响应）
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import error_response
from .services import ExcelExportService, CsvExportService
from .word_service import WordExportService
from .pdf_service import PdfExportService


# 导入模板表头映射（type -> 表头列表）
_TEMPLATE_HEADERS = {
    'projects': ['项目名称', '项目编号', '负责人', '当前阶段', '状态', '开始时间', '预计结束'],
    'history_projects': [
        '项目名称', '项目编号', '负责人ID', '当前阶段', '状态',
        '开始时间', '预计结束', '实际结束', '简介', '优先级',
    ],
    'finance_budget': ['项目编号', '奖金总额', '其他收入', '统计周期'],
    'tasks': ['任务标题', '项目编号', '指派给', '截止时间'],
    'contributions': ['项目编号', '贡献人', '贡献类型', '贡献内容', '权重', '统计周期'],
    'ip_applications': ['成果名称', '内部编号', '成果类型', '关联项目编号', '主导撰写人'],
}


class ExportTemplateView(APIView):
    """
    下载导入模板视图
    GET /api/v1/exports/template/?type=<模板类型>
    返回仅含表头的空白 Excel 模板
    """
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        export_type = request.query_params.get('type')
        fmt = request.query_params.get('file_format', 'xlsx').lower()
        project_id = request.query_params.get('project_id')
        ip_id = request.query_params.get('ip_id')

        if not export_type:
            return error_response(message='请提供 type 参数指定导出类型', code=1001)

        try:
            # ============ Excel 导出 ============
            if fmt == 'xlsx':
                if export_type == 'projects':
                    return ExcelExportService.export_projects()
                elif export_type == 'finance_budget':
                    return ExcelExportService.export_finance_budget()
                elif export_type == 'finance_detail':
                    if not project_id:
                        return error_response(message='经费明细导出需提供 project_id', code=1001)
                    return ExcelExportService.export_finance_detail(project_id)
                elif export_type == 'tasks':
                    return ExcelExportService.export_tasks(project_id)
                elif export_type == 'contributions':
                    if not project_id:
                        return error_response(message='贡献记录导出需提供 project_id', code=1001)
                    return ExcelExportService.export_contributions(project_id)
                elif export_type == 'ip_applications':
                    return ExcelExportService.export_ip_applications()
                elif export_type == 'members':
                    return ExcelExportService.export_members()
                elif export_type == 'competitions':
                    return ExcelExportService.export_competitions()

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
                    return PdfExportService.export_finance_report(project_id)

            # ============ CSV 导出 ============
            elif fmt == 'csv':
                if export_type == 'projects':
                    return CsvExportService.export_projects()
                elif export_type == 'finance_budget':
                    return CsvExportService.export_finance_budget()
                elif export_type == 'finance_detail':
                    if not project_id:
                        return error_response(message='经费明细导出需提供 project_id', code=1001)
                    return CsvExportService.export_finance_detail(project_id)
                elif export_type == 'tasks':
                    return CsvExportService.export_tasks(project_id)
                elif export_type == 'contributions':
                    if not project_id:
                        return error_response(message='贡献记录导出需提供 project_id', code=1001)
                    return CsvExportService.export_contributions(project_id)
                elif export_type == 'ip_applications':
                    return CsvExportService.export_ip_applications()
                elif export_type == 'members':
                    return CsvExportService.export_members()
                elif export_type == 'competitions':
                    return CsvExportService.export_competitions()

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
