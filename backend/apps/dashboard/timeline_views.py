"""
Dashboard 扩展视图
P1: 统一时间线聚合、比赛矩阵、晋级漏斗、项目日历、Gantt 历程条
所有接口权限: IsAuthenticated
"""
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Q, Count
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.permissions import IsInternalTeamMember
from common.response import success_response
from apps.projects.models import Project, ProjectStageLog
from apps.tasks.models import Task
from apps.finance.models import FinanceExpense
from apps.files.models import FileAsset
from apps.competitions.models import Competition
from apps.contributions.models import Contribution
from apps.intellectual_property.models import (
    IntellectualPropertyApplication,
    IPReturnRecord,
)


def _fmt_dt(dt):
    """格式化日期时间为 ISO 字符串"""
    if dt is None:
        return None
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)


def _fmt_date(d):
    """格式化日期为 YYYY-MM-DD"""
    if d is None:
        return None
    return d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)


class TimelineEventView(APIView):
    """
    统一时间线聚合接口
    GET /api/v1/dashboard/timeline/
    查询参数:
      - project_id: 按项目过滤(可选)
      - start_date: 开始日期(可选, YYYY-MM-DD)
      - end_date: 结束日期(可选, YYYY-MM-DD)
      - event_type: 精确事件类型过滤(可选，多个类型用逗号分隔)
      - limit: 返回条数(默认 200)
    返回: 统一格式的事件列表, 按时间倒序排列
    """
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        event_type = request.query_params.get('event_type')
        try:
            limit = min(max(int(request.query_params.get('limit', 200)), 1), 500)
        except (TypeError, ValueError):
            limit = 200

        events = []

        # ---- 解析日期过滤 ----
        date_filter = Q()
        if start_date:
            date_filter &= Q(created_at__date__gte=start_date)
        if end_date:
            date_filter &= Q(created_at__date__lte=end_date)

        # ---- 1. 项目阶段变更 ----
        stage_log_qs = ProjectStageLog.objects.select_related(
            'project', 'operator'
        ).order_by('-created_at')
        if project_id:
            stage_log_qs = stage_log_qs.filter(project_id=project_id)
        if start_date:
            stage_log_qs = stage_log_qs.filter(created_at__date__gte=start_date)
        if end_date:
            stage_log_qs = stage_log_qs.filter(created_at__date__lte=end_date)

        stage_choices = dict(Project.Stage.choices)
        for log in stage_log_qs[:limit]:
            from_name = stage_choices.get(log.from_stage, '初始') if log.from_stage else '初始'
            to_name = stage_choices.get(log.to_stage, '')
            events.append({
                'id': f'stage_{log.id}',
                'type': 'stage_change',
                'title': f'{log.project.name} 阶段变更',
                'description': f'{from_name} → {to_name}',
                'timestamp': _fmt_dt(log.created_at),
                'date': _fmt_date(log.created_at.date()) if log.created_at else None,
                'project_id': log.project_id,
                'project_name': log.project.name,
                'project_code': log.project.code,
                'operator_name': log.operator.name if log.operator else '系统',
                'metadata': {
                    'from_stage': log.from_stage,
                    'to_stage': log.to_stage,
                    'from_stage_display': from_name,
                    'to_stage_display': to_name,
                    'note': log.note,
                },
            })

        # ---- 2. 任务创建与完成 ----
        task_qs = Task.objects.select_related('project', 'assignee').order_by('-created_at')
        if project_id:
            task_qs = task_qs.filter(project_id=project_id)
        if start_date:
            task_qs = task_qs.filter(created_at__date__gte=start_date)
        if end_date:
            task_qs = task_qs.filter(created_at__date__lte=end_date)

        for task in task_qs[:limit]:
            # 创建事件
            events.append({
                'id': f'task_created_{task.id}',
                'type': 'task_created',
                'title': f'新任务: {task.title}',
                'description': f'指派给 {task.assignee.name if task.assignee else "未指派"}',
                'timestamp': _fmt_dt(task.created_at),
                'date': _fmt_date(task.created_at.date()) if task.created_at else None,
                'project_id': task.project_id,
                'project_name': task.project.name,
                'project_code': task.project.code,
                'operator_name': task.creator.name if task.creator else '',
                'metadata': {
                    'task_id': task.id,
                    'status': task.status,
                    'deadline': _fmt_dt(task.deadline),
                },
            })
            # 完成事件
            if task.completed_at:
                events.append({
                    'id': f'task_done_{task.id}',
                    'type': 'task_completed',
                    'title': f'任务完成: {task.title}',
                    'description': f'{task.assignee.name if task.assignee else ""} 完成了任务',
                    'timestamp': _fmt_dt(task.completed_at),
                    'date': _fmt_date(task.completed_at.date()) if task.completed_at else None,
                    'project_id': task.project_id,
                    'project_name': task.project.name,
                    'project_code': task.project.code,
                    'operator_name': task.assignee.name if task.assignee else '',
                    'metadata': {'task_id': task.id},
                })

        # ---- 3. 比赛关键节点 ----
        comp_qs = Competition.objects.select_related('project').order_by('-created_at')
        if project_id:
            comp_qs = comp_qs.filter(project_id=project_id)

        for comp in comp_qs[:limit]:
            level_display = comp.get_level_display()
            date_fields = [
                ('register_date', '报名截止', 'competition_register'),
                ('material_deadline', '材料截止', 'competition_material'),
                ('review_date', '网评日期', 'competition_review'),
                ('defense_date', '答辩日期', 'competition_defense'),
                ('result_date', '结果公布', 'competition_result'),
            ]
            for field_name, label, evt_type in date_fields:
                field_val = getattr(comp, field_name, None)
                if field_val:
                    desc = f'{comp.name}({level_display}) {label}'
                    if comp.is_awarded and field_name == 'result_date':
                        desc += f' - 获奖等级: {comp.award_level}'
                    events.append({
                        'id': f'comp_{evt_type}_{comp.id}',
                        'type': evt_type,
                        'title': f'比赛节点: {comp.name}',
                        'description': desc,
                        'timestamp': f'{field_val}T00:00:00',
                        'date': _fmt_date(field_val),
                        'project_id': comp.project_id,
                        'project_name': comp.project.name if comp.project else '',
                        'project_code': comp.project.code if comp.project else '',
                        'operator_name': '',
                        'metadata': {
                            'competition_id': comp.id,
                            'level': comp.level,
                            'level_display': level_display,
                            'is_promoted': comp.is_promoted,
                            'is_awarded': comp.is_awarded,
                            'award_level': comp.award_level,
                        },
                    })

        # ---- 4. 经费支出 ----
        expense_qs = FinanceExpense.objects.select_related(
            'project', 'spender'
        ).order_by('-expense_date')
        if project_id:
            expense_qs = expense_qs.filter(project_id=project_id)
        if start_date:
            expense_qs = expense_qs.filter(expense_date__gte=start_date)
        if end_date:
            expense_qs = expense_qs.filter(expense_date__lte=end_date)

        for exp in expense_qs[:limit]:
            events.append({
                'id': f'expense_{exp.id}',
                'type': 'expense',
                'title': f'经费支出: {exp.title}',
                'description': f'{exp.get_category_display()} ¥{exp.amount}',
                'timestamp': f'{exp.expense_date}T00:00:00' if exp.expense_date else _fmt_dt(exp.created_at),
                'date': _fmt_date(exp.expense_date),
                'project_id': exp.project_id,
                'project_name': exp.project.name,
                'project_code': exp.project.code,
                'operator_name': exp.spender.name if exp.spender else '',
                'metadata': {
                    'expense_id': exp.id,
                    'amount': str(exp.amount),
                    'category': exp.category,
                    'category_display': exp.get_category_display(),
                },
            })

        # ---- 5. 文件上传 ----
        file_qs = FileAsset.objects.select_related('project', 'uploader').order_by('-created_at')
        if project_id:
            file_qs = file_qs.filter(project_id=project_id)
        if start_date:
            file_qs = file_qs.filter(created_at__date__gte=start_date)
        if end_date:
            file_qs = file_qs.filter(created_at__date__lte=end_date)

        for f in file_qs[:limit]:
            events.append({
                'id': f'file_{f.id}',
                'type': 'file_upload',
                'title': f'文件上传: {f.name}',
                'description': f'{f.get_level_display()} · {f.content_type or "未知类型"}',
                'timestamp': _fmt_dt(f.created_at),
                'date': _fmt_date(f.created_at.date()) if f.created_at else None,
                'project_id': f.project_id,
                'project_name': f.project.name if f.project else '公共文件',
                'project_code': f.project.code if f.project else '',
                'operator_name': f.uploader.name if f.uploader else '',
                'metadata': {
                    'file_id': f.id,
                    'level': f.level,
                    'size': f.size,
                    'version': f.version,
                },
            })

        # ---- 6. 知识产权状态节点 ----
        ip_qs = IntellectualPropertyApplication.objects.select_related(
            'related_project'
        ).order_by('-created_at')
        if project_id:
            ip_qs = ip_qs.filter(related_project_id=project_id)

        for ip in ip_qs[:limit]:
            ip_date_fields = [
                ('submit_date', '提交申请', 'ip_submit'),
                ('accepted_date', '已受理', 'ip_accepted'),
                ('authorized_date', '已授权/登记', 'ip_authorized'),
            ]
            for field_name, label, evt_type in ip_date_fields:
                field_val = getattr(ip, field_name, None)
                if field_val:
                    events.append({
                        'id': f'{evt_type}_{ip.id}',
                        'type': evt_type,
                        'title': f'知识产权: {ip.title}',
                        'description': f'{ip.get_ip_type_display()} {label}',
                        'timestamp': f'{field_val}T00:00:00',
                        'date': _fmt_date(field_val),
                        'project_id': ip.related_project_id,
                        'project_name': ip.related_project.name if ip.related_project else '',
                        'project_code': ip.related_project.code if ip.related_project else '',
                        'operator_name': '',
                        'metadata': {
                            'ip_id': ip.id,
                            'ip_type': ip.ip_type,
                            'status': ip.status,
                        },
                    })

        # 知识产权退回记录
        return_qs = IPReturnRecord.objects.select_related(
            'application', 'application__related_project', 'responsible_user'
        ).order_by('-return_time')
        if project_id:
            return_qs = return_qs.filter(application__related_project_id=project_id)

        for ret in return_qs[:limit]:
            events.append({
                'id': f'ip_return_{ret.id}',
                'type': 'ip_return',
                'title': f'知识产权退回: {ret.application.title}',
                'description': f'{ret.get_return_source_display()} - {ret.return_reason[:50]}',
                'timestamp': _fmt_dt(ret.return_time),
                'date': _fmt_date(ret.return_time.date()) if ret.return_time else None,
                'project_id': ret.application.related_project_id,
                'project_name': ret.application.related_project.name if ret.application.related_project else '',
                'project_code': ret.application.related_project.code if ret.application.related_project else '',
                'operator_name': ret.responsible_user.name if ret.responsible_user else '',
                'metadata': {
                    'ip_id': ret.application_id,
                    'return_source': ret.return_source,
                    'responsibility_type': ret.responsibility_type,
                },
            })

        # ---- 7. 贡献记录 ----
        contrib_qs = Contribution.objects.select_related(
            'user', 'project'
        ).order_by('-created_at')
        if project_id:
            contrib_qs = contrib_qs.filter(project_id=project_id)
        if start_date:
            contrib_qs = contrib_qs.filter(created_at__date__gte=start_date)
        if end_date:
            contrib_qs = contrib_qs.filter(created_at__date__lte=end_date)

        for contrib in contrib_qs[:limit]:
            events.append({
                'id': f'contrib_{contrib.id}',
                'type': 'contribution',
                'title': f'贡献记录: {contrib.user.name}',
                'description': f'{contrib.get_contribution_type_display()} - {contrib.content[:50] if contrib.content else contrib.description[:50]}',
                'timestamp': _fmt_dt(contrib.created_at),
                'date': _fmt_date(contrib.created_at.date()) if contrib.created_at else None,
                'project_id': contrib.project_id,
                'project_name': contrib.project.name if contrib.project else '',
                'project_code': contrib.project.code if contrib.project else '',
                'operator_name': contrib.user.name,
                'metadata': {
                    'contribution_id': contrib.id,
                    'contribution_type': contrib.contribution_type,
                    'status': contrib.status,
                    'weight': str(contrib.weight),
                },
            })

        # 比赛和知识产权事件使用业务日期而不是 created_at；统一在聚合后按
        # event.date 再过滤一次，确保时间线的日期筛选对所有事件类型一致生效。
        if start_date:
            events = [
                event for event in events
                if event.get('date') and event['date'] >= start_date
            ]
        if end_date:
            events = [
                event for event in events
                if event.get('date') and event['date'] <= end_date
            ]

        # ---- 按 event_type 过滤 ----
        if event_type:
            event_types = {
                item.strip()
                for item in event_type.split(',')
                if item.strip()
            }
            if event_types:
                events = [e for e in events if e['type'] in event_types]

        # ---- 按时间倒序排序 ----
        events.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

        # ---- 截断 ----
        events = events[:limit]

        data = {
            'total': len(events),
            'events': events,
        }
        return success_response(data, message='success')


class CompetitionMatrixView(APIView):
    """
    比赛矩阵视图
    GET /api/v1/dashboard/competition-matrix/
    返回项目×比赛级别的交叉矩阵
    每行:一个项目在各级别(校赛/市赛/省赛/国赛)的比赛数、获奖数、晋级数
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        levels = ['school', 'city', 'province', 'national']
        level_names = {
            'school': '校赛', 'city': '市赛', 'province': '省赛', 'national': '国赛',
        }

        projects = Project.objects.prefetch_related('competitions').order_by('-created_at')
        matrix = []
        # 列汇总
        level_totals = {lv: {'total': 0, 'awarded': 0, 'promoted': 0} for lv in levels}

        for project in projects:
            row = {
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.code,
                'current_stage': project.current_stage,
                'current_stage_display': project.get_current_stage_display(),
                'status': project.status,
                'cells': {},
            }
            for lv in levels:
                comps = project.competitions.filter(level=lv)
                total = comps.count()
                awarded = comps.filter(is_awarded=True).count()
                promoted = comps.filter(is_promoted=True).count()
                row['cells'][lv] = {
                    'level_display': level_names[lv],
                    'total': total,
                    'awarded': awarded,
                    'promoted': promoted,
                }
                level_totals[lv]['total'] += total
                level_totals[lv]['awarded'] += awarded
                level_totals[lv]['promoted'] += promoted
            matrix.append(row)

        data = {
            'levels': [{'key': lv, 'name': level_names[lv]} for lv in levels],
            'matrix': matrix,
            'level_totals': level_totals,
        }
        return success_response(data, message='success')


class CompetitionFunnelView(APIView):
    """
    比赛晋级漏斗
    GET /api/v1/dashboard/competition-funnel/
    按级别(school→city→province→national)统计参加数、晋级数、晋级率、获奖数
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        levels = ['school', 'city', 'province', 'national']
        level_names = {
            'school': '校赛', 'city': '市赛', 'province': '省赛', 'national': '国赛',
        }

        funnel_data = []
        for lv in levels:
            total = Competition.objects.filter(level=lv).count()
            promoted = Competition.objects.filter(level=lv, is_promoted=True).count()
            awarded = Competition.objects.filter(level=lv, is_awarded=True).count()
            ongoing = Competition.objects.filter(
                level=lv, status__in=['preparing', 'ongoing']
            ).count()
            completed = Competition.objects.filter(
                level=lv, status='completed'
            ).count()
            rate = round(promoted / total * 100, 1) if total > 0 else 0
            award_rate = round(awarded / total * 100, 1) if total > 0 else 0
            funnel_data.append({
                'level': lv,
                'level_display': level_names[lv],
                'total': total,
                'promoted': promoted,
                'awarded': awarded,
                'ongoing': ongoing,
                'completed': completed,
                'promotion_rate': rate,
                'award_rate': award_rate,
            })

        data = {
            'funnel': funnel_data,
            'total_competitions': sum(d['total'] for d in funnel_data),
            'total_promoted': sum(d['promoted'] for d in funnel_data),
            'total_awarded': sum(d['awarded'] for d in funnel_data),
        }
        return success_response(data, message='success')


class ProjectCalendarView(APIView):
    """
    项目日历数据
    GET /api/v1/dashboard/calendar/
    返回日历热力图数据:每个日期的事件数量
    查询参数:
      - year: 指定年份(默认当前年)
      - project_id: 按项目过滤
    """
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        import datetime
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        project_id = request.query_params.get('project_id')

        # 收集所有日期的事件
        date_events = defaultdict(list)

        # 比赛日期
        comp_qs = Competition.objects.select_related('project')
        if project_id:
            comp_qs = comp_qs.filter(project_id=project_id)
        date_fields = [
            ('register_date', '报名截止'),
            ('defense_date', '答辩'),
            ('result_date', '结果公布'),
            ('material_deadline', '材料截止'),
            ('review_date', '网评'),
        ]
        for comp in comp_qs:
            for field, label in date_fields:
                val = getattr(comp, field, None)
                if val and val.year == year:
                    date_events[val.isoformat()].append({
                        'type': 'competition',
                        'label': f'{comp.name} {label}',
                        'level': comp.level,
                        'level_display': comp.get_level_display(),
                    })

        # 任务截止
        task_qs = Task.objects.select_related('project')
        if project_id:
            task_qs = task_qs.filter(project_id=project_id)
        for task in task_qs:
            if task.deadline and task.deadline.year == year:
                d = task.deadline.date().isoformat()
                date_events[d].append({
                    'type': 'task_deadline',
                    'label': f'任务截止: {task.title}',
                })

        # 项目里程碑(开始/计划结束)
        proj_qs = Project.objects.all()
        if project_id:
            proj_qs = proj_qs.filter(id=project_id)
        for proj in proj_qs:
            if proj.start_date and proj.start_date.year == year:
                date_events[proj.start_date.isoformat()].append({
                    'type': 'project_start',
                    'label': f'{proj.name} 启动',
                })
            if proj.planned_end_date and proj.planned_end_date.year == year:
                date_events[proj.planned_end_date.isoformat()].append({
                    'type': 'project_end',
                    'label': f'{proj.name} 计划结束',
                })

        # 经费支出
        exp_qs = FinanceExpense.objects.select_related('project')
        if project_id:
            exp_qs = exp_qs.filter(project_id=project_id)
        for exp in exp_qs:
            if exp.expense_date and exp.expense_date.year == year:
                date_events[exp.expense_date.isoformat()].append({
                    'type': 'expense',
                    'label': f'支出: {exp.title} ¥{exp.amount}',
                })

        # 转为列表
        calendar_data = []
        for date_str, evts in sorted(date_events.items()):
            calendar_data.append({
                'date': date_str,
                'count': len(evts),
                'events': evts,
            })

        data = {
            'year': year,
            'calendar': calendar_data,
        }
        return success_response(data, message='success')


class ProjectGanttView(APIView):
    """
    项目 Gantt 历程条数据
    GET /api/v1/dashboard/gantt/
    返回所有项目的时间轴数据,用于横向 Gantt 图展示
    查询参数:
      - project_id: 按项目过滤
      - status: 按项目状态过滤
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        status = request.query_params.get('status')

        qs = Project.objects.prefetch_related('stage_logs', 'competitions').order_by('start_date')
        if project_id:
            qs = qs.filter(id=project_id)
        if status:
            qs = qs.filter(status=status)

        gantt_data = []
        for project in qs:
            # 收集阶段变更历史
            stage_logs = list(project.stage_logs.select_related('operator').order_by('created_at'))
            stages = []
            stage_choices = dict(Project.Stage.choices)
            for log in stage_logs:
                stages.append({
                    'stage': log.to_stage,
                    'stage_display': stage_choices.get(log.to_stage, ''),
                    'date': _fmt_date(log.created_at.date()) if log.created_at else None,
                    'operator': log.operator.name if log.operator else '系统',
                })

            # 比赛里程碑
            milestones = []
            for comp in project.competitions.all():
                if comp.defense_date:
                    milestones.append({
                        'date': _fmt_date(comp.defense_date),
                        'label': f'{comp.name} 答辩',
                        'level': comp.level,
                        'level_display': comp.get_level_display(),
                        'is_awarded': comp.is_awarded,
                        'award_level': comp.award_level,
                    })
                if comp.result_date:
                    milestones.append({
                        'date': _fmt_date(comp.result_date),
                        'label': f'{comp.name} 结果',
                        'level': comp.level,
                        'level_display': comp.get_level_display(),
                        'is_awarded': comp.is_awarded,
                        'award_level': comp.award_level,
                    })

            gantt_data.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.code,
                'start_date': _fmt_date(project.start_date),
                'planned_end_date': _fmt_date(project.planned_end_date),
                'actual_end_date': _fmt_date(project.actual_end_date),
                'current_stage': project.current_stage,
                'current_stage_display': project.get_current_stage_display(),
                'status': project.status,
                'status_display': project.get_status_display(),
                'priority': project.priority,
                'leader_name': project.leader.name if project.leader else '',
                'stages': stages,
                'milestones': milestones,
            })

        data = {
            'total': len(gantt_data),
            'projects': gantt_data,
        }
        return success_response(data, message='success')


class PublicPortalView(APIView):
    """
    公共展示主页数据(无需认证)
    GET /api/v1/dashboard/public-portal/
    返回团队成果概览:统计数据、获奖项目、知识产权成果、核心成员、公开公告、项目统计
    """
    permission_classes = []  # 公开访问

    def get(self, request):
        from apps.users.models import User
        from apps.notifications.models import Announcement
        from django.db.models import Count
        from .portal_models import PortalPublication
        from .portal_serializers import PortalSettingsSerializer
        from .portal_views import get_portal_settings

        publications = list(
            PortalPublication.objects.filter(is_public=True).order_by(
                '-is_featured', 'display_order', 'id'
            )
        )
        publications_by_type = defaultdict(list)
        for publication in publications:
            publications_by_type[publication.content_type].append(publication)

        # 统计数据
        total_projects = Project.objects.count()
        # 有获奖比赛的项目数 或 已获奖/已结项阶段的项目数
        awarded_project_ids = Competition.objects.filter(
            is_awarded=True
        ).values_list('project_id', flat=True).distinct()
        awarded_projects = Project.objects.filter(
            Q(id__in=awarded_project_ids) |
            Q(current_stage=Project.Stage.AWARDED)
        ).distinct().count()
        closed_projects = Project.objects.filter(
            status=Project.Status.CLOSED
        ).count()
        total_competitions = Competition.objects.count()
        awarded_competitions = Competition.objects.filter(is_awarded=True).count()
        # 已授权成果在完成正式归档前也属于已形成的知识产权成果。
        # 只统计 archived 会让门户明明展示已授权成果，顶部数量却仍为 0。
        total_ip = IntellectualPropertyApplication.objects.filter(
            status__in=(
                IntellectualPropertyApplication.Status.AUTHORIZED,
                IntellectualPropertyApplication.Status.ARCHIVED,
            )
        ).count()

        # P17: 项目统计（总数 / 进行中 / 已完成）
        active_projects = Project.objects.filter(
            status=Project.Status.ACTIVE
        ).count()
        completed_projects = Project.objects.filter(
            status=Project.Status.CLOSED
        ).count()
        project_statistics = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
        }

        # P17: 公开公告（已发布且 is_public=True，按置顶/发布时间倒序取最新 10 条）
        announcement_list = []
        public_announcements = Announcement.objects.select_related('author').filter(
            status=Announcement.Status.PUBLISHED,
            is_public=True,
        ).order_by('-is_pinned', '-published_at', '-created_at')[:10]
        for ann in public_announcements:
            announcement_list.append({
                'id': ann.id,
                'title': ann.title,
                'content': ann.content,
                'category': ann.category,
                'category_display': ann.get_category_display(),
                'is_pinned': ann.is_pinned,
                'author_name': ann.author.name if ann.author else '',
                'published_at': _fmt_dt(ann.published_at),
            })

        # 项目成果只展示经过逐项公开确认的项目。
        awarded_project_list = []
        project_publications = publications_by_type[
            PortalPublication.ContentType.PROJECT
        ][:20]
        project_map = {
            project.id: project
            for project in Project.objects.select_related('leader').filter(
                id__in=[item.object_id for item in project_publications]
            ).prefetch_related('competitions')
        }
        for publication in project_publications:
            proj = project_map.get(publication.object_id)
            if not proj:
                continue
            awards = proj.competitions.filter(is_awarded=True)
            award_info = []
            for a in awards:
                award_info.append({
                    'competition_name': a.name,
                    'level': a.level,
                    'level_display': a.get_level_display(),
                    'award_level': a.award_level,
                })
            awarded_project_list.append({
                'project_id': proj.id,
                'project_name': publication.custom_title or proj.name,
                'project_code': proj.code,
                'intro': (
                    publication.custom_summary
                    or (proj.intro[:200] if proj.intro else '')
                ),
                'leader_name': proj.leader.name if proj.leader else '',
                'start_date': _fmt_date(proj.start_date),
                'awards': award_info,
                'is_featured': publication.is_featured,
                'image_url': publication.image_url,
            })

        # 知识产权同样仅展示经过逐项公开确认的条目。
        ip_results = []
        ip_publications = publications_by_type[
            PortalPublication.ContentType.IP_APPLICATION
        ][:20]
        ip_map = {
            item.id: item
            for item in IntellectualPropertyApplication.objects.filter(
                id__in=[publication.object_id for publication in ip_publications]
            )
        }
        for publication in ip_publications:
            ip = ip_map.get(publication.object_id)
            if not ip:
                continue
            ip_results.append({
                'ip_id': ip.id,
                'title': publication.custom_title or ip.title,
                'ip_type': ip.ip_type,
                'ip_type_display': ip.get_ip_type_display(),
                'application_code': ip.application_code,
                'authorized_date': _fmt_date(ip.authorized_date),
                'intro': (
                    publication.custom_summary
                    or (ip.intro[:200] if ip.intro else '')
                ),
                'is_featured': publication.is_featured,
                'image_url': publication.image_url,
            })

        # 成员必须同时满足管理员发布和成员本人授权。
        core_members = []
        member_publications = [
            item for item in publications_by_type[PortalPublication.ContentType.MEMBER]
            if item.member_consent
        ][:20]
        member_map = {
            user.id: user
            for user in User.objects.filter(
                is_active=True,
                id__in=[item.object_id for item in member_publications],
            ).annotate(proj_count=Count('project_memberships'))
        }
        for publication in member_publications:
            user = member_map.get(publication.object_id)
            if not user:
                continue
            core_members.append({
                'user_id': user.id,
                'name': publication.custom_title or user.name,
                'global_role': user.global_role,
                'global_role_display': user.get_global_role_display(),
                'grade': user.grade,
                'major': user.major,
                'project_count': user.proj_count,
                'summary': publication.custom_summary,
                'is_featured': publication.is_featured,
            })

        data = {
            'stats': {
                'total_projects': total_projects,
                'awarded_projects': awarded_projects,
                'closed_projects': closed_projects,
                'total_competitions': total_competitions,
                'awarded_competitions': awarded_competitions,
                'total_ip': total_ip,
            },
            'project_statistics': project_statistics,
            'announcements': announcement_list,
            'awarded_projects': awarded_project_list,
            'ip_results': ip_results,
            'core_members': core_members,
            'settings': PortalSettingsSerializer(get_portal_settings()).data,
        }
        return success_response(data, message='success')
