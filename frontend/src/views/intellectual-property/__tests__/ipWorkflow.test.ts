import { describe, expect, it } from 'vitest'
import type { IPApplicationListItem, IPStatus } from '@/types/intellectualProperty'
import {
  buildProjectParticipantOptions,
  buildTeacherConfirmerOptions,
  getAvailableIPWorkflowActions,
  getIPWorkflowActions,
  mapIPApplicationsToTodos,
  normalizeIPProjectFilter,
  resolveIPCreateProjectDeepLink,
} from '../ipWorkflow'

function application(status: IPStatus, id = 1): IPApplicationListItem {
  return {
    id,
    title: `申请 ${id}`,
    application_code: `IP-${id}`,
    ip_type: 'software_copyright',
    status,
    return_count: 0,
    created_at: '2026-07-20T08:00:00Z',
    updated_at: '2026-07-24T09:30:00Z',
  }
}

describe('mapIPApplicationsToTodos', () => {
  it('maps paginated application results into actionable todo items', () => {
    const result = mapIPApplicationsToTodos({
      count: 3,
      next: null,
      previous: null,
      results: [application('writing', 1), application('leader_review', 2), application('returned', 3)],
    })

    expect(result).toEqual([
      expect.objectContaining({ application_id: 1, type: 'writing', created_at: '2026-07-24T09:30:00Z' }),
      expect.objectContaining({ application_id: 2, type: 'review', description: '完成项目负责人审核' }),
      expect.objectContaining({ application_id: 3, type: 'return_fix', title: '申请 3' }),
    ])
  })

  it('accepts the non-paginated fallback and ignores terminal states', () => {
    expect(mapIPApplicationsToTodos([application('archived'), application('terminated', 2)])).toEqual([])
  })
})

describe('IP list deep-link filters', () => {
  it('normalizes route project_id into the backend related_project filter', () => {
    expect(normalizeIPProjectFilter('24')).toBe(24)
    expect(normalizeIPProjectFilter(['19', '20'])).toBe(19)
    expect(normalizeIPProjectFilter('invalid')).toBeUndefined()
    expect(normalizeIPProjectFilter('0')).toBeUndefined()
  })

  it('only prefills create links for projects in the accessible leader list', () => {
    expect(resolveIPCreateProjectDeepLink('24', [{ id: 24 }])).toBe(24)
    expect(resolveIPCreateProjectDeepLink('25', [{ id: 24 }])).toBeNull()
    expect(resolveIPCreateProjectDeepLink('invalid', [{ id: 24 }])).toBeNull()
  })
})

describe('IP workflow actions', () => {
  it('matches the backend legal transition targets', () => {
    const expected: Record<IPStatus, IPStatus[]> = {
      draft: ['writing', 'paused', 'terminated', 'deferred'],
      writing: ['leader_review', 'paused', 'terminated', 'deferred'],
      leader_review: ['teacher_confirm', 'writing', 'paused', 'deferred'],
      teacher_confirm: ['research_office_review', 'leader_review', 'paused', 'deferred'],
      research_office_review: ['accepted', 'returned', 'paused', 'deferred'],
      returned: ['modifying', 'paused', 'terminated', 'deferred'],
      modifying: ['paused', 'terminated', 'deferred'],
      resubmitted: ['research_office_review', 'accepted', 'returned', 'paused', 'deferred'],
      accepted: ['authorized', 'paused'],
      authorized: ['archived'],
      archived: [],
      paused: ['draft', 'writing', 'leader_review', 'teacher_confirm', 'research_office_review', 'modifying', 'deferred'],
      terminated: [],
      deferred: ['draft'],
    }

    for (const [status, targets] of Object.entries(expected) as Array<[IPStatus, IPStatus[]]>) {
      expect(getIPWorkflowActions(status).map((item) => item.targetStatus)).toEqual(targets)
    }
    expect(getIPWorkflowActions('authorized')[0].kind).toBe('archive')
    expect(
      getIPWorkflowActions('research_office_review')
        .find((item) => item.targetStatus === 'returned')?.kind,
    ).toBe('return')
  })

  it('hides institution decisions from non-privileged resubmission handlers', () => {
    expect(
      getAvailableIPWorkflowActions('resubmitted', true, false)
        .map((item) => item.targetStatus),
    ).toEqual(['research_office_review', 'paused', 'deferred'])

    expect(
      getAvailableIPWorkflowActions('resubmitted', true, true)
        .map((item) => item.targetStatus),
    ).toEqual(['research_office_review', 'accepted', 'returned', 'paused', 'deferred'])
  })
})

describe('project participant options', () => {
  it('uses only project members and keeps the project leader once', () => {
    const options = buildProjectParticipantOptions(
      { leader: 7, leader_name: '负责人' },
      [
        {
          id: 1,
          project: 2,
          user: 7,
          user_name: '负责人',
          user_detail: { id: 7, name: '负责人', email: 'leader@example.com' },
          role_in_project: 'leader',
          joined_at: '2026-07-01T00:00:00Z',
        },
        {
          id: 2,
          project: 2,
          user: 8,
          user_name: '项目成员',
          user_detail: { id: 8, name: '项目成员', email: 'member@example.com' },
          role_in_project: 'core',
          joined_at: '2026-07-01T00:00:00Z',
        },
      ],
    )

    expect(options).toEqual([
      {
        id: 7,
        name: '负责人',
        username: undefined,
        email: 'leader@example.com',
        global_role: undefined,
        membership_status: undefined,
        is_active: undefined,
      },
      {
        id: 8,
        name: '项目成员',
        username: undefined,
        email: 'member@example.com',
        global_role: undefined,
        membership_status: undefined,
        is_active: undefined,
      },
    ])
  })

  it('excludes inactive project memberships and only offers valid teachers', () => {
    const participants = buildProjectParticipantOptions(
      { leader: 7, leader_name: '负责人' },
      [
        {
          id: 1,
          project: 2,
          user: 8,
          user_name: '已离项成员',
          user_detail: {
            id: 8,
            name: '已离项成员',
            membership_status: 'active',
            is_active: true,
          },
          role_in_project: 'member',
          status: 'exited',
          joined_at: '2026-07-01T00:00:00Z',
        },
      ],
    )
    expect(participants.map((item) => item.id)).toEqual([7])

    const teachers = buildTeacherConfirmerOptions([
      {
        id: 10,
        username: 'teacher',
        email: 'teacher@example.com',
        name: '有效老师',
        global_role: 'teacher',
        membership_status: 'active',
        is_active: true,
        date_joined: '2026-07-01T00:00:00Z',
      },
      {
        id: 11,
        username: 'member',
        email: 'member@example.com',
        name: '普通成员',
        global_role: 'member',
        membership_status: 'active',
        is_active: true,
        date_joined: '2026-07-01T00:00:00Z',
      },
      {
        id: 12,
        username: 'old-teacher',
        email: 'old-teacher@example.com',
        name: '离队老师',
        global_role: 'teacher',
        membership_status: 'exited',
        is_active: false,
        date_joined: '2026-07-01T00:00:00Z',
      },
    ])

    expect(teachers.map((item) => item.id)).toEqual([10])
  })
})
