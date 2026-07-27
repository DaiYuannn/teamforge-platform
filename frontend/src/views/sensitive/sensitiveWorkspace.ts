import type { UserRole } from '@/types'

export type SensitiveWorkspaceTab = 'my-data' | 'requests' | 'pending'

const APPROVER_ROLES = new Set<UserRole>(['sys_admin', 'teacher', 'sens_approver'])

export function canApproveSensitive(role: UserRole | ''): boolean {
  return role !== '' && APPROVER_ROLES.has(role)
}

export function normalizeSensitiveWorkspaceTab(
  value: unknown,
  role: UserRole | '',
): SensitiveWorkspaceTab {
  const requested = Array.isArray(value) ? value[0] : value
  if (requested === 'requests') return 'requests'
  if (requested === 'pending' && canApproveSensitive(role)) return 'pending'
  return 'my-data'
}
