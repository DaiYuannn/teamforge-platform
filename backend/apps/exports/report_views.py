"""
项目报告导出视图
GET /api/v1/exports/project-report/<project_id>/
返回 Word 文件下载（python-docx 不可用时降级为纯文本）
"""
from urllib.parse import quote

from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import error_response
from .report_templates import generate_project_report, HAS_PYTHON_DOCX


class ProjectReportView(APIView):
    """
    项目完整报告导出视图
    - GET: 下载项目 Word 报告（含基本信息、阶段历程、比赛记录、经费统计、成员列表、知识产权、贡献汇总）
    - 权限: IsAuthenticated
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            file_stream = generate_project_report(project_id)
        except ValueError as e:
            # 项目不存在等业务校验失败
            return error_response(message=str(e), code=1004)
        except Exception as e:
            return error_response(message=f'报告生成失败：{e}', code=1006)

        # 根据是否可用 python-docx 决定文件类型与扩展名
        if HAS_PYTHON_DOCX:
            content_type = (
                'application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document'
            )
            ext = 'docx'
        else:
            content_type = 'text/plain; charset=utf-8'
            ext = 'txt'

        # 文件名兼容中文（RFC 5987）
        filename = quote(f'项目报告_{project_id}')
        response = FileResponse(
            file_stream,
            content_type=content_type,
        )
        response['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{filename}.{ext}"
        )
        return response
