"""
日历同步视图
- CalendarFeedView: 返回 iCal 格式日历（任务/截止日期）

接口：
- GET /api/v1/common/calendar/
"""
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from common.response import success_response


def _escape_ical(text):
    """转义 iCal 文本"""
    if not text:
        return ''
    return (
        str(text)
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _to_ical_dt(dt):
    """datetime -> iCal UTC 时间字符串"""
    if dt is None:
        return ''
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    dt_utc = dt.astimezone(dt_timezone.utc)
    return dt_utc.strftime('%Y%m%dT%H%M%SZ')


class CalendarFeedView(APIView):
    """
    日历同步
    GET /api/v1/common/calendar/
    返回当前用户相关任务/截止日期的 iCal 格式日历
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.tasks.models import Task

        # 收集当前用户负责的任务（带截止时间）
        tasks = Task.objects.filter(
            assignee=request.user,
        ).exclude(deadline__isnull=True).select_related('project')

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//TeamManagement//Calendar//ZH',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
        ]

        now_stamp = _to_ical_dt(timezone.now())
        count = 0
        for task in tasks:
            due = getattr(task, 'deadline', None)
            lines.append('BEGIN:VEVENT')
            lines.append(f'UID:task-{task.id}@team-management')
            lines.append(f'DTSTAMP:{now_stamp}')
            if due:
                lines.append(f'DTSTART:{_to_ical_dt(due)}')
                lines.append(f'DTEND:{_to_ical_dt(due)}')
            lines.append(f'SUMMARY:{_escape_ical(task.title)}')
            project_name = getattr(task.project, 'name', '') if task.project_id else ''
            if project_name:
                lines.append(f'LOCATION:{_escape_ical(project_name)}')
            status_map = {
                'todo': 'NEEDS-ACTION',
                'in_progress': 'IN-PROCESS',
                'done': 'COMPLETED',
                'cancelled': 'CANCELLED',
            }
            ical_status = status_map.get(getattr(task, 'status', ''), 'NEEDS-ACTION')
            lines.append(f'STATUS:{ical_status}')
            lines.append('END:VEVENT')
            count += 1

        lines.append('END:VCALENDAR')
        ical_content = '\r\n'.join(lines)

        # 默认返回 JSON 包装；支持 ?output=ical 直接返回 text/calendar
        fmt = request.query_params.get('output', 'json')
        if fmt == 'ical':
            return Response(ical_content, content_type='text/calendar; charset=utf-8')

        return success_response({
            'format': 'ical',
            'event_count': count,
            'calendar': ical_content,
        })
