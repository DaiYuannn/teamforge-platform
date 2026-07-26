import { describe, expect, it } from 'vitest'
import { notificationRelatedRoute } from '@/utils/notificationRoute'
import type { Notification } from '@/types'

function notice(type?: string, id?: number): Notification {
  return {
    id: 1,
    recipient: 1,
    title: '通知',
    content: '内容',
    is_read: false,
    created_at: '2026-07-26 09:00:00',
    related_object_type: type,
    related_object_id: id,
  }
}

describe('notification related routes', () => {
  it('maps detail routes that require a valid id', () => {
    expect(notificationRelatedRoute(notice('project', 9))).toBe('/projects/9')
    expect(notificationRelatedRoute(notice('task', 12))).toEqual({
      path: '/tasks',
      query: { task_id: '12' },
    })
    expect(notificationRelatedRoute(notice('project'))).toBeNull()
  })

  it.each([
    ['competition_result', '/competitions'],
    ['scheduled_report', '/reports'],
    ['contribution', '/contributions/pending'],
    ['ranking_objection', '/contributions'],
    ['ip_return', '/intellectual-property/todo'],
    ['ip_objection', '/intellectual-property/todo'],
    ['flexible_work_schedule', '/members/schedule'],
    ['sensitive_request', '/sensitive/pending'],
    ['finance_expense', '/finance'],
    ['finance_income', '/finance'],
    ['FinanceBudget', '/finance'],
  ])('maps %s to its business list', (type, expected) => {
    expect(notificationRelatedRoute(notice(type, 3))).toBe(expected)
  })

  it('uses the localized notification category when no object relation is present', () => {
    expect(notificationRelatedRoute({ ...notice(), notification_type: 'report' })).toBe('/reports')
    expect(notificationRelatedRoute({ ...notice(), notification_type: 'finance' })).toBe('/finance')
    expect(notificationRelatedRoute({ ...notice(), notification_type: 'announcement' })).toBe('/announcements')
  })

  it('returns null for notifications without a supported relation', () => {
    expect(notificationRelatedRoute(notice('unknown', 1))).toBeNull()
    expect(notificationRelatedRoute(notice())).toBeNull()
  })
})
