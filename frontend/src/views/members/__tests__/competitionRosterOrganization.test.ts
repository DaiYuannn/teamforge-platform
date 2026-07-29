import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Competition, CompetitionParticipant, User } from '@/types'
import type { TeamCandidate, TeamMemberRole } from '@/api/teams'

const {
  getEventsMock,
  getCompetitionsMock,
  getParticipantsMock,
  getCandidatesMock,
  addParticipantMock,
} = vi.hoisted(() => ({
  getEventsMock: vi.fn(),
  getCompetitionsMock: vi.fn(),
  getParticipantsMock: vi.fn(),
  getCandidatesMock: vi.fn(),
  addParticipantMock: vi.fn(),
}))

vi.mock('@/api/competitions', () => ({
  getCompetitionEvents: getEventsMock,
  getCompetitions: getCompetitionsMock,
  getCompetitionParticipants: getParticipantsMock,
  getCompetitionParticipantCandidates: getCandidatesMock,
  addCompetitionParticipant: addParticipantMock,
  updateCompetitionParticipant: vi.fn(),
  deleteCompetitionParticipant: vi.fn(),
}))

import CompetitionMemberPicker from '../CompetitionMemberPicker.vue'
import CompetitionEntryCard from '../CompetitionEntryCard.vue'
import CompetitionRosterPanel from '../CompetitionRosterPanel.vue'

function competitionEntry(
  id: number,
  project: number,
  projectName: string,
): Competition {
  return {
    id,
    project,
    project_name: projectName,
    name: '全国创新赛',
    level: 'national',
    status: 'preparing',
    organizer: '赛事组委会',
    is_promoted: false,
    is_awarded: false,
    award_level: '',
    not_promoted_reason: '',
    improvement_suggestion: '',
    review_summary: '',
    current_stage: '材料准备',
    can_manage: true,
    created_at: '2026-07-29T00:00:00Z',
  }
}

function participant(
  id: number,
  competition: number,
  user: number,
): CompetitionParticipant {
  return {
    id,
    competition,
    user,
    role: 'member',
    participation_status: 'confirmed',
    responsibility: '',
  }
}

function participantUser(id: number, name: string, school: string): User {
  return {
    id,
    username: `member-${id}`,
    email: `member-${id}@test.com`,
    name,
    school,
    global_role: 'member',
    is_active: true,
    date_joined: '2026-07-29T00:00:00Z',
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  getEventsMock.mockResolvedValue({
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        id: 5,
        name: '全国创新赛',
        edition: '2026 届',
        organizer: '赛事组委会',
        entry_count: 2,
      },
    ],
  })
  getCompetitionsMock.mockResolvedValue({
    count: 2,
    next: null,
    previous: null,
    results: [
      competitionEntry(11, 101, '项目甲'),
      competitionEntry(12, 102, '项目乙'),
    ],
  })
  getParticipantsMock.mockImplementation((entryId: number) =>
    Promise.resolve([participant(entryId + 100, entryId, 9)]),
  )
  getCandidatesMock.mockResolvedValue([])
  addParticipantMock.mockResolvedValue({})
})

describe('competition roster organization', () => {
  it('defaults to one event and groups its entries by project without globally deduplicating people', async () => {
    const wrapper = shallowMount(CompetitionRosterPanel, {
      global: {
        stubs: {
          CompetitionEntryCard: true,
          EmptyState: true,
        },
      },
    })

    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      selectedEventId: number
      projectGroups: Array<{ projectId: number }>
      participantsByEntry: Record<number, CompetitionParticipant[]>
    }
    expect(vm.selectedEventId).toBe(5)
    expect(getCompetitionsMock).toHaveBeenCalledWith({
      event: 5,
      page: 1,
      page_size: 100,
    })
    expect(vm.projectGroups.map((group) => group.projectId)).toEqual([101, 102])
    expect(vm.participantsByEntry[11]?.[0]?.user).toBe(9)
    expect(vm.participantsByEntry[12]?.[0]?.user).toBe(9)
  })

  it('sends a one-character keyword together with school, role and status filters', async () => {
    const wrapper = shallowMount(CompetitionMemberPicker, {
      props: {
        visible: true,
        competitionId: 11,
        competitionName: '项目甲',
        existingUserIds: [9],
      },
      global: {
        stubs: {
          'el-dialog': { template: '<div />' },
          'el-table-column': { template: '<div />' },
        },
      },
    })
    const vm = wrapper.vm as unknown as {
      filters: {
        search: string
        school: string
        team_role?: TeamMemberRole
        membership_status: string
      }
      loadCandidates: () => Promise<void>
      candidateSelectable: (candidate: TeamCandidate) => boolean
    }
    Object.assign(vm.filters, {
      search: '刘',
      school: '示范大学',
      team_role: 'co_lead',
      membership_status: 'active',
    })
    await vm.loadCandidates()

    expect(getCandidatesMock).toHaveBeenCalledWith(11, {
      search: '刘',
      school: '示范大学',
      team_role: 'co_lead',
      membership_status: 'active',
    })
    const baseCandidate: TeamCandidate = {
      id: 9,
      name: '刘宇成',
      email: 'liu@example.com',
      membership_status: 'active',
      is_active: true,
    }
    expect(vm.candidateSelectable(baseCandidate)).toBe(false)
    expect(vm.candidateSelectable({ ...baseCandidate, id: 10 })).toBe(true)
  })

  it('keeps identity, school and participation-status filters local to each entry card', () => {
    const first = participant(101, 11, 9)
    first.role = 'leader'
    first.user_detail = participantUser(9, '刘宇成', '示例大学')
    const second = participant(102, 11, 10)
    second.role = 'member'
    second.participation_status = 'planned'
    second.user_detail = participantUser(10, '其他成员', '其他大学')
    const wrapper = shallowMount(CompetitionEntryCard, {
      props: {
        entry: competitionEntry(11, 101, '项目甲'),
        participants: [second, first],
      },
      global: {
        stubs: {
          CompetitionMemberPicker: true,
          'el-dialog': { template: '<div />' },
          'el-table-column': { template: '<div />' },
        },
      },
    })
    const vm = wrapper.vm as unknown as {
      participantFilters: { role?: string; school: string; status?: string }
      filteredParticipants: CompetitionParticipant[]
    }

    expect(vm.filteredParticipants.map((row) => row.user)).toEqual([9, 10])
    Object.assign(vm.participantFilters, {
      role: 'leader',
      school: '示例大学',
      status: 'confirmed',
    })
    expect(vm.filteredParticipants.map((row) => row.user)).toEqual([9])
  })
})

describe('team organization view contract', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/views/members/TeamManageView.vue'),
    'utf8',
  )

  it('makes competition configuration the default and keeps only root teams in the directory', () => {
    expect(source).toContain(
      "const activeView = ref<'competition' | 'directory'>('competition')",
    )
    expect(source).toContain('<CompetitionRosterPanel />')
    expect(source).toContain(
      'const rootTeams = computed(() => teams.value.filter((team) => !team.parent))',
    )
    expect(source).not.toContain('v-for="team in displayTeams"')
  })
})
