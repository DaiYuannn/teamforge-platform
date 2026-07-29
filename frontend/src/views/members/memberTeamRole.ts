import type { Member, TeamRole } from '@/types'

export const TEAM_ROLE_OPTIONS: Array<{ value: TeamRole; label: string }> = [
  { value: 'teacher', label: '查看老师（只读）' },
  { value: 'owner', label: '主负责人' },
  { value: 'co_lead', label: '共同负责人' },
  { value: 'admin', label: '团队管理员' },
  { value: 'advisor', label: '顾问' },
  { value: 'member', label: '团队成员' },
  { value: 'external', label: '外部协作者' },
]

const TEAM_ROLE_LABELS = Object.fromEntries(
  TEAM_ROLE_OPTIONS.map((option) => [option.value, option.label]),
) as Record<TeamRole, string>

export function teamRoleText(member: Pick<Member, 'team_role' | 'team_role_display'>): string {
  return member.team_role_display?.trim()
    || (member.team_role ? TEAM_ROLE_LABELS[member.team_role] : '')
    || '未分组'
}

export function teamRoleTagType(role?: TeamRole): string {
  if (!role) return 'info'
  if (role === 'teacher') return 'warning'
  if (role === 'owner') return 'danger'
  if (role === 'co_lead' || role === 'admin') return 'primary'
  if (role === 'external') return 'info'
  return 'success'
}
