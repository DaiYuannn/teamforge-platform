import { describe, expect, it } from 'vitest'
import { calendarEventDisplayLabel, calendarEventTypeLabel } from '@/utils/calendarEvents'

describe('calendar event labels', () => {
  it.each([
    ['competition', '比赛'],
    ['task_deadline', '任务截止'],
    ['project_start', '项目启动'],
    ['project_end', '项目计划结束'],
    ['expense', '经费支出'],
  ])('translates %s', (type, expected) => {
    expect(calendarEventTypeLabel(type)).toBe(expected)
  })

  it('keeps a localized level label and hides unknown event codes', () => {
    expect(calendarEventDisplayLabel({ type: 'competition', level_display: '国家级' })).toBe('国家级')
    expect(calendarEventTypeLabel('new_server_code')).toBe('其他事件')
  })
})
