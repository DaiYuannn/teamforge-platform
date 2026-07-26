"""
手动触发提醒任务的管理命令
直接同步调用任务函数（不通过 Celery 异步执行）
用法:
    python manage.py run_reminder task_overdue
    python manage.py run_reminder leader_update
    python manage.py run_reminder flexible_schedule
    python manage.py run_reminder ip_returns
    python manage.py run_reminder ip_objections
    python manage.py run_reminder contributions
    python manage.py run_reminder sensitive
    python manage.py run_reminder all
"""
from django.core.management.base import BaseCommand

from apps.notifications.tasks import (
    check_task_overdue,
    check_leader_update,
    check_competition_deadlines,
    remind_flexible_schedule,
    check_ip_returns,
    check_ip_objections,
    check_pending_contributions,
    check_sensitive_requests,
)


class Command(BaseCommand):
    """手动触发提醒任务"""

    help = '手动触发提醒任务（同步执行，不通过 Celery）'

    # 任务名称与任务函数的映射
    TASK_MAP = {
        'task_overdue': ('任务延期提醒', check_task_overdue),
        'leader_update': ('负责人更新提醒', check_leader_update),
        'competition_deadlines': ('比赛关键节点提醒', check_competition_deadlines),
        'flexible_schedule': ('灵活工作时间填写提醒', remind_flexible_schedule),
        'ip_returns': ('知识产权退回修改提醒', check_ip_returns),
        'ip_objections': ('知识产权异议提醒', check_ip_objections),
        'contributions': ('贡献记录待审核提醒', check_pending_contributions),
        'sensitive': ('敏感资料申请待审批提醒', check_sensitive_requests),
    }

    def add_arguments(self, parser):
        """添加命令参数"""
        parser.add_argument(
            'task_name',
            type=str,
            help='任务名称: task_overdue/leader_update/flexible_schedule/'
                 'competition_deadlines/ip_returns/ip_objections/contributions/sensitive/all',
        )

    def handle(self, *args, **options):
        """执行命令"""
        task_name = options['task_name']

        if task_name == 'all':
            # 执行所有任务
            self.stdout.write(self.style.SUCCESS('开始执行所有提醒任务...'))
            for name, (desc, func) in self.TASK_MAP.items():
                self.stdout.write(self.style.HTTP_INFO(f'\n>>> 执行: {desc}'))
                try:
                    result = func.apply() if hasattr(func, 'apply') else func()
                    # shared_task 直接调用会返回 EagerResult，取 .get()
                    if hasattr(result, 'get'):
                        result = result.get()
                    self.stdout.write(self.style.SUCCESS(f'    结果: {result}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    执行失败: {e}'))
            self.stdout.write(self.style.SUCCESS('\n所有提醒任务执行完毕'))
        elif task_name in self.TASK_MAP:
            desc, func = self.TASK_MAP[task_name]
            self.stdout.write(self.style.HTTP_INFO(f'开始执行: {desc}'))
            try:
                result = func.apply() if hasattr(func, 'apply') else func()
                if hasattr(result, 'get'):
                    result = result.get()
                self.stdout.write(self.style.SUCCESS(f'执行完成: {result}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'执行失败: {e}'))
        else:
            self.stdout.write(self.style.ERROR(
                f'未知任务名称: {task_name}\n'
                f'可选任务: {"/".join(list(self.TASK_MAP.keys()) + ["all"])}'
            ))
