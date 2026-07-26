"""定时报表 Celery 任务。"""
import logging

from celery import shared_task

from .scheduled_report_models import ScheduledReportExecution
from .scheduled_report_service import (
    claim_due_schedule_execution_ids,
    execute_scheduled_report,
    fail_scheduled_report_execution,
)

logger = logging.getLogger(__name__)


@shared_task(name='apps.exports.tasks.run_due_scheduled_reports')
def run_due_scheduled_reports():
    execution_ids = []
    for execution_id in claim_due_schedule_execution_ids():
        claimed_execution = None
        try:
            claimed_execution = (
                ScheduledReportExecution.objects.select_related('schedule')
                .get(pk=execution_id)
            )
            execution = execute_scheduled_report(
                claimed_execution.schedule,
                trigger=ScheduledReportExecution.Trigger.SCHEDULED,
                execution=claimed_execution,
            )
        except ScheduledReportExecution.DoesNotExist:
            logger.warning('定时报表领取记录 %s 已不存在', execution_id)
            continue
        except Exception as exc:
            logger.exception('定时报表领取记录 %s 执行异常', execution_id)
            if claimed_execution is None:
                continue
            try:
                execution = fail_scheduled_report_execution(
                    claimed_execution,
                    exc,
                )
            except Exception:
                logger.exception('定时报表领取记录 %s 失败状态写回异常', execution_id)
                continue
        execution_ids.append(execution.pk)
    return {'executed': len(execution_ids), 'execution_ids': execution_ids}
