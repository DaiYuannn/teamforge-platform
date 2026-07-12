"""
PDF 导出服务
使用 weasyprint 将 HTML 模板渲染为 PDF
注意：weasyprint 依赖系统级 GTK/Pango 库，导入失败时方法会抛出可被视图捕获的异常，
因此采用惰性导入（不在模块顶层导入），保证 `manage.py check` 在未安装原生库时也能通过
所有导出接口直接返回文件流 HttpResponse
"""
from django.http import HttpResponse
from django.template.loader import render_to_string


def _render_html_to_pdf(html_string, filename):
    """
    将 HTML 字符串渲染为 PDF 并包装为 HttpResponse
    惰性导入 weasyprint；若依赖不可用，回退为 HTML 文件下载并附说明
    """
    try:
        from weasyprint import HTML
    except Exception as e:  # pragma: no cover - 依赖环境
        # PDF 依赖不可用：回退为 HTML 文件下载，并附加提示信息
        fallback_note = (
            '<div style="padding:16px;border:1px solid #f0ad4e;background:#fcf8e3;'
            'color:#8a6d3b;margin-bottom:16px;font-size:14px;">'
            '提示：服务器未安装 PDF 渲染依赖（weasyprint/GTK/Pango），暂无法生成 PDF，'
            '已自动回退为 HTML 文件下载。如需 PDF，请联系管理员安装相关服务端依赖。'
            f'<br><span style="color:#a94442;font-size:12px;">依赖错误：{e}</span>'
            '</div>'
        )
        fallback_html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<title>{filename}</title></head><body>'
            + fallback_note
            + html_string
            + '</body></html>'
        )
        response = HttpResponse(fallback_html, content_type='text/html')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}.html"
        return response

    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}.pdf"
    return response


def _get_project_context(project_id):
    """构建项目报告 PDF 上下文"""
    from apps.projects.models import Project
    from apps.finance.models import FinanceBudget, FinanceExpense
    from apps.tasks.models import Task
    from apps.contributions.models import Contribution

    try:
        project = Project.objects.select_related('leader').get(id=project_id)
    except Project.DoesNotExist:
        raise ValueError('项目不存在')

    budget = FinanceBudget.objects.filter(project=project).first()
    expenses = list(FinanceExpense.objects.filter(project=project).order_by('-expense_date'))
    tasks = list(Task.objects.filter(project=project).order_by('deadline'))
    contributions = list(Contribution.objects.filter(project=project).order_by('-created_at'))

    return {
        'project': project,
        'budget': budget,
        'expenses': expenses,
        'tasks': tasks,
        'contributions': contributions,
        'title': f'项目报告：{project.name}',
    }


def _get_finance_context(project_id=None):
    """构建经费汇总报告 PDF 上下文"""
    from apps.finance.models import FinanceBudget, FinanceExpense
    from apps.projects.models import Project

    if project_id:
        budgets = list(FinanceBudget.objects.filter(project_id=project_id).select_related('project'))
        expenses = list(FinanceExpense.objects.filter(project_id=project_id).select_related('project'))
    else:
        budgets = list(FinanceBudget.objects.select_related('project').all())
        expenses = list(FinanceExpense.objects.select_related('project').all())

    # 汇总
    total_bonus = sum(float(b.bonus_amount) for b in budgets)
    total_used = sum(float(b.used_amount) for b in budgets)
    total_remaining = sum(float(b.remaining_amount) for b in budgets)

    return {
        'budgets': budgets,
        'expenses': expenses,
        'total_bonus': total_bonus,
        'total_used': total_used,
        'total_remaining': total_remaining,
        'title': '经费汇总报告',
    }


class PdfExportService:
    """PDF 导出服务"""

    @staticmethod
    def export_project_report(project_id):
        """
        导出项目报告 PDF
        渲染 reports/project_report.html 模板为 PDF
        :param project_id: 项目ID
        """
        context = _get_project_context(project_id)
        html_string = render_to_string('reports/project_report.html', context)
        project = context['project']
        return _render_html_to_pdf(html_string, f'项目报告_{project.name}')

    @staticmethod
    def export_finance_report(project_id=None):
        """
        导出经费汇总报告 PDF
        渲染 reports/finance_report.html 模板为 PDF
        :param project_id: 可选，指定项目
        """
        context = _get_finance_context(project_id)
        html_string = render_to_string('reports/finance_report.html', context)
        suffix = f'_{context["budgets"][0].project.name}' if project_id and context['budgets'] else ''
        return _render_html_to_pdf(html_string, f'经费汇总报告{suffix}')
