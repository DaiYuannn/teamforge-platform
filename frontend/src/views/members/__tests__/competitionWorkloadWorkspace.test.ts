import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Competition, CompetitionParticipant } from '@/types'
import type {
  CompetitionWorkItem,
  WorkloadAssessment,
  WorkloadObjection,
} from '@/types/workload'

const {
  getEventsMock,
  getCompetitionsMock,
  getParticipantsMock,
  getWorkItemsMock,
  getAssessmentsMock,
  getObjectionsMock,
} = vi.hoisted(() => ({
  getEventsMock: vi.fn(),
  getCompetitionsMock: vi.fn(),
  getParticipantsMock: vi.fn(),
  getWorkItemsMock: vi.fn(),
  getAssessmentsMock: vi.fn(),
  getObjectionsMock: vi.fn(),
}))

vi.mock('@/api/competitions', () => ({
  getCompetitionEvents: getEventsMock,
  getCompetitions: getCompetitionsMock,
  getCompetitionParticipants: getParticipantsMock,
}))

vi.mock('@/api/workloads', () => ({
  getCompetitionWorkItems: getWorkItemsMock,
  getWorkloadAssessments: getAssessmentsMock,
  getWorkloadObjections: getObjectionsMock,
  createCompetitionWorkItem: vi.fn(),
  updateCompetitionWorkItem: vi.fn(),
  deleteCompetitionWorkItem: vi.fn(),
  saveWorkloadAssessmentDraft: vi.fn(),
  publishWorkloadAssessment: vi.fn(),
  createWorkloadObjection: vi.fn(),
  resolveWorkloadObjection: vi.fn(),
}))

import CompetitionWorkloadWorkspace from '../CompetitionWorkloadWorkspace.vue'

function entry(overrides: Partial<Competition> = {}): Competition {
  return {
    id: 11,
    event: 5,
    event_name: '全国创新赛',
    event_edition: '2026 届',
    entry_name: 'A 队',
    project: 101,
    project_name: '智创项目',
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
    ...overrides,
  }
}

function participant(
  id: number,
  user: number,
  role: CompetitionParticipant['role'],
  participationStatus: CompetitionParticipant['participation_status'] = 'confirmed',
): CompetitionParticipant {
  return {
    id,
    competition: 11,
    user,
    role,
    participation_status: participationStatus,
    user_detail: {
      id: user,
      username: `user-${user}`,
      email: `user-${user}@example.com`,
      name: `成员 ${user}`,
      global_role: 'member',
      is_active: true,
      date_joined: '2026-01-01T00:00:00Z',
    },
  }
}

function workItem(): CompetitionWorkItem {
  return {
    id: 21,
    competition: 11,
    event_name: '全国创新赛',
    event_edition: '2026 届',
    entry_name: 'A 队',
    project: 101,
    project_name: '智创项目',
    assignee: 8,
    assignee_name: '成员 8',
    collaborators: [],
    collaborator_names: [],
    reviewer: null,
    reviewer_name: '',
    title: '完成答辩稿',
    description: '',
    deadline: '2026-08-10',
    priority: 'medium',
    status: 'todo',
    status_display: '待开始',
    completed_at: null,
    completion_note: '',
    reference_note: '完成组内评审',
    subtasks: [],
    created_by_name: '负责人',
    can_manage: true,
    can_edit: true,
    can_review: true,
    created_at: '2026-07-29T00:00:00Z',
    updated_at: '2026-07-29T00:00:00Z',
  }
}

function assessment(
  overrides: Partial<WorkloadAssessment> = {},
): WorkloadAssessment {
  return {
    id: 31,
    competition: 11,
    project: 101,
    project_name: '智创项目',
    event_name: '全国创新赛',
    event_edition: '2026 届',
    entry_name: 'A 队',
    version: 1,
    status: 'published',
    status_display: '已发布',
    decision_note: '',
    decided_by_name: '负责人',
    published_at: '2026-07-29T00:00:00Z',
    is_current: true,
    allocations: [
      {
        id: 41,
        user: 8,
        user_name: '成员 8',
        percentage: '100.00',
        rationale: '完成核心交付',
      },
    ],
    allocation_total: '100.00',
    objection_count: 0,
    can_manage: true,
    can_object: true,
    ...overrides,
  }
}

function objection(): WorkloadObjection {
  return {
    id: 51,
    allocation: 41,
    assessment: 31,
    competition: 11,
    allocation_user: 8,
    allocation_user_name: '成员 8',
    raised_by: 9,
    raised_by_name: '成员 9',
    reason: '希望复核交付依据',
    status: 'open',
    status_display: '待处理',
    response: '',
    resolved_by_name: '',
    created_at: '2026-07-29T00:00:00Z',
    resolved_at: null,
    can_resolve: true,
  }
}

function mountWorkspace(mode: 'mine' | 'team') {
  return shallowMount(CompetitionWorkloadWorkspace, {
    props: { mode },
    global: {
      stubs: {
        PageHeader: {
          template: '<header><slot name="actions" /></header>',
        },
        EmptyState: true,
        'el-button': {
          props: ['disabled'],
          template: '<button :disabled="disabled"><slot /></button>',
        },
        'el-alert': true,
        'el-select': true,
        'el-option': true,
        'el-tabs': true,
        'el-tab-pane': true,
        'el-table': true,
        'el-table-column': true,
        'el-dialog': true,
        'el-form': true,
        'el-form-item': true,
      },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
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
        entry_count: 1,
      },
    ],
  })
  getCompetitionsMock.mockResolvedValue({
    count: 1,
    next: null,
    previous: null,
    results: [entry()],
  })
  getParticipantsMock.mockResolvedValue([
    participant(1, 8, 'leader'),
    participant(2, 9, 'member'),
  ])
  getWorkItemsMock.mockResolvedValue([workItem()])
  getAssessmentsMock.mockResolvedValue([assessment()])
  getObjectionsMock.mockResolvedValue([objection()])
})

describe('competition workload context', () => {
  it('does not load or enable a workspace before both event and entry are selected', async () => {
    const wrapper = mountWorkspace('mine')
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      contextReady: boolean
      selectedEventId: number | null
      selectedCompetitionId: number | null
    }
    expect(vm.contextReady).toBe(false)
    expect(vm.selectedEventId).toBeNull()
    expect(vm.selectedCompetitionId).toBeNull()
    expect(getWorkItemsMock).not.toHaveBeenCalled()
  })

  it('keeps team task and assessment upload actions disabled before context is complete', async () => {
    const wrapper = mountWorkspace('team')
    await flushPromises()

    const actionButtons = wrapper.findAll('header button')
    expect(actionButtons.map((button) => button.text())).toEqual([
      '登记成员任务',
      '填写有效工作量占比',
    ])
    expect(actionButtons.every((button) => button.attributes('disabled') !== undefined))
      .toBe(true)
  })

  it('cascades event to entry and scopes the mine workspace with mine=1', async () => {
    const wrapper = mountWorkspace('mine')
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      contextReady: boolean
      selectedEventId: number | null
      selectedCompetitionId: number | null
      workItems: CompetitionWorkItem[]
    }

    vm.selectedEventId = 5
    await flushPromises()
    expect(getCompetitionsMock).toHaveBeenCalledWith({
      event: 5,
      page: 1,
      page_size: 100,
    })

    vm.selectedCompetitionId = 11
    await flushPromises()

    expect(vm.contextReady).toBe(true)
    expect(getWorkItemsMock).toHaveBeenCalledWith({ competition: 11, mine: 1 })
    expect(getAssessmentsMock).toHaveBeenCalledWith(11)
    expect(getObjectionsMock).toHaveBeenCalledWith(11)
    expect(getParticipantsMock).toHaveBeenCalledWith(11)
    expect(vm.workItems).toHaveLength(1)
  })

  it('clears the selected entry and old workspace immediately when the event changes', async () => {
    const wrapper = mountWorkspace('mine')
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      selectedEventId: number | null
      selectedCompetitionId: number | null
      workItems: CompetitionWorkItem[]
    }

    vm.selectedEventId = 5
    await flushPromises()
    vm.selectedCompetitionId = 11
    await flushPromises()
    expect(vm.workItems).toHaveLength(1)

    getCompetitionsMock.mockResolvedValueOnce({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })
    vm.selectedEventId = 6
    await flushPromises()

    expect(vm.selectedCompetitionId).toBeNull()
    expect(vm.workItems).toEqual([])
  })

  it('does not add mine=1 to the team task query', async () => {
    const wrapper = mountWorkspace('team')
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      selectedEventId: number | null
      selectedCompetitionId: number | null
    }
    vm.selectedEventId = 5
    await flushPromises()
    vm.selectedCompetitionId = 11
    await flushPromises()

    expect(getWorkItemsMock).toHaveBeenCalledWith({ competition: 11 })
  })
})

describe('effective workload allocation', () => {
  it('only allocates leader/member participants who have not withdrawn', async () => {
    getParticipantsMock.mockResolvedValue([
      participant(1, 8, 'leader'),
      participant(2, 9, 'member'),
      participant(3, 10, 'advisor'),
      participant(4, 11, 'member', 'withdrawn'),
    ])
    const wrapper = mountWorkspace('team')
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      selectedEventId: number | null
      selectedCompetitionId: number | null
      eligibleParticipants: CompetitionParticipant[]
      assessmentForm: {
        allocations: Array<{ user: number; percentage: number }>
      }
      allocationTotalValid: boolean
      openAssessmentDialog: () => void
    }
    vm.selectedEventId = 5
    await flushPromises()
    vm.selectedCompetitionId = 11
    await flushPromises()

    expect(vm.eligibleParticipants.map((item) => item.user)).toEqual([8, 9])
    vm.openAssessmentDialog()
    expect(vm.assessmentForm.allocations.map((item) => item.user)).toEqual([8, 9])

    vm.assessmentForm.allocations[0]!.percentage = 60
    vm.assessmentForm.allocations[1]!.percentage = 39.99
    await flushPromises()
    expect(vm.allocationTotalValid).toBe(false)

    vm.assessmentForm.allocations[1]!.percentage = 40
    await flushPromises()
    expect(vm.allocationTotalValid).toBe(true)
  })

  it('prefers the highest draft version when reopening allocation editing', async () => {
    getAssessmentsMock.mockResolvedValue([
      assessment({ id: 31, version: 4, status: 'published', is_current: true }),
      assessment({
        id: 32,
        version: 5,
        status: 'draft',
        status_display: '草稿',
        published_at: null,
        is_current: false,
        decision_note: '第五版草稿',
      }),
    ])
    const wrapper = mountWorkspace('team')
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      selectedEventId: number | null
      selectedCompetitionId: number | null
      currentAssessment: WorkloadAssessment
      assessmentForm: { decision_note: string }
      openAssessmentDialog: () => void
    }
    vm.selectedEventId = 5
    await flushPromises()
    vm.selectedCompetitionId = 11
    await flushPromises()

    expect(vm.currentAssessment.id).toBe(32)
    vm.openAssessmentDialog()
    expect(vm.assessmentForm.decision_note).toBe('第五版草稿')
  })
})

describe('competition work item responsibility chain', () => {
  it('distinguishes task owner, collaborators, reviewer and subtask owners', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/members/CompetitionWorkloadWorkspace.vue'),
      'utf8',
    )
    expect(source).toContain('任务负责人')
    expect(source).toContain('协作者')
    expect(source).toContain('任务验收人')
    expect(source).toContain('子任务与具体负责人')
    expect(source).toContain('待验收')
    expect(source).toContain('提交验收结果')
  })
})
