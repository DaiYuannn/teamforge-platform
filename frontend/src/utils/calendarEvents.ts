export const CALENDAR_EVENT_TYPE_LABELS: Record<string, string> = {
  competition: '比赛',
  task_deadline: '任务截止',
  project_start: '项目启动',
  project_end: '项目计划结束',
  expense: '经费支出',
}

export function calendarEventTypeLabel(type: unknown): string {
  return CALENDAR_EVENT_TYPE_LABELS[String(type || '')] || '其他事件'
}

export function calendarEventDisplayLabel(event: { type?: string; level_display?: string }): string {
  return event.level_display || calendarEventTypeLabel(event.type)
}
