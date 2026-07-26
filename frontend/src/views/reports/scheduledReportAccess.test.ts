import { describe, expect, it } from 'vitest'
import { canManageScheduledReport } from './scheduledReportAccess'

describe('scheduled report access', () => {
  it('honors the backend can_manage decision when present', () => {
    expect(canManageScheduledReport(
      { created_by: 3, can_manage: false },
      { id: 3, global_role: 'member' },
    )).toBe(false)
    expect(canManageScheduledReport(
      { created_by: 9, can_manage: true },
      { id: 3, global_role: 'member' },
    )).toBe(true)
  })

  it('falls back to owner and privileged role checks for older responses', () => {
    expect(canManageScheduledReport(
      { created_by: 3 },
      { id: 3, global_role: 'member' },
    )).toBe(true)
    expect(canManageScheduledReport(
      { created_by: 9 },
      { id: 3, global_role: 'teacher' },
    )).toBe(true)
    expect(canManageScheduledReport(
      { created_by: 9 },
      { id: 3, global_role: 'member' },
    )).toBe(false)
  })
})
