import type {
  TeamMember,
  TeamMemberFilters,
  TeamMemberQueryParams,
} from '@/api/teams'

function normalize(value?: string): string {
  return (value || '').trim().toLocaleLowerCase()
}

export function hasTeamMemberFilters(filters: TeamMemberFilters): boolean {
  return Boolean(filters.role || filters.school.trim() || filters.status)
}

export function toTeamMemberQueryParams(
  filters: TeamMemberFilters,
): TeamMemberQueryParams {
  return {
    ...(filters.role ? { role: filters.role } : {}),
    ...(filters.school.trim() ? { school: filters.school.trim() } : {}),
    ...(filters.status ? { status: filters.status } : {}),
  }
}

/**
 * 服务端负责决定成员的重要性顺序；这里只做兜底筛选，不重新排序。
 * 这样即使某个部署尚未支持全部筛选参数，负责人看到的顺序仍与后端一致。
 */
export function filterTeamMembers(
  members: TeamMember[],
  filters: TeamMemberFilters,
): TeamMember[] {
  const school = normalize(filters.school)
  return members.filter((member) => (
    (!filters.role || member.role === filters.role)
    && (!filters.status || member.status === filters.status)
    && (!school || normalize(member.user_school) === school)
  ))
}
