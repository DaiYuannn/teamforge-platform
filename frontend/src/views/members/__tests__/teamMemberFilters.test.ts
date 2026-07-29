import { describe, expect, it } from 'vitest'
import type { TeamMember, TeamMemberFilters } from '@/api/teams'
import {
  filterTeamMembers,
  hasTeamMemberFilters,
  toTeamMemberQueryParams,
} from '../teamMemberFilters'

function member(
  id: number,
  role: TeamMember['role'],
  school: string,
  status: TeamMember['status'] = 'active',
): TeamMember {
  return {
    id,
    team: 2,
    user: id,
    user_name: `成员 ${id}`,
    user_email: `member-${id}@example.com`,
    user_school: school,
    role,
    status,
    joined_at: '2026-07-29T00:00:00Z',
  }
}

describe('team member filters', () => {
  const backendImportanceOrder = [
    member(1, 'teacher', '示例大学'),
    member(2, 'owner', '示例大学'),
    member(3, 'co_lead', '示例大学'),
    member(4, 'member', '合作大学', 'on_leave'),
    member(5, 'external', '合作大学', 'exited'),
  ]

  it('preserves the backend importance order while applying filters', () => {
    const filters: TeamMemberFilters = {
      role: undefined,
      school: '示例大学',
      status: 'active',
    }

    expect(filterTeamMembers(backendImportanceOrder, filters).map((item) => item.id))
      .toEqual([1, 2, 3])
  })

  it('returns the complete ordered list after filters are cleared', () => {
    const cleared: TeamMemberFilters = {
      role: undefined,
      school: '',
      status: undefined,
    }

    expect(hasTeamMemberFilters(cleared)).toBe(false)
    expect(filterTeamMembers(backendImportanceOrder, cleared).map((item) => item.id))
      .toEqual([1, 2, 3, 4, 5])
    expect(toTeamMemberQueryParams(cleared)).toEqual({})
  })

  it('builds compact backend parameters for active filters', () => {
    const filters: TeamMemberFilters = {
      role: 'member',
      school: ' 合作大学 ',
      status: 'on_leave',
    }

    expect(hasTeamMemberFilters(filters)).toBe(true)
    expect(toTeamMemberQueryParams(filters)).toEqual({
      role: 'member',
      school: '合作大学',
      status: 'on_leave',
    })
  })
})
