import type { ScheduledReport } from '@/api/reports'
import type { User } from '@/types'

export function canManageScheduledReport(
  schedule: Pick<ScheduledReport, 'created_by' | 'can_manage'>,
  user: Pick<User, 'id' | 'global_role'> | null | undefined,
): boolean {
  if (typeof schedule.can_manage === 'boolean') return schedule.can_manage
  if (!user) return false
  return ['teacher', 'sys_admin'].includes(user.global_role) || schedule.created_by === user.id
}
