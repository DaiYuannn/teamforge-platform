import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PaginatedResponse } from '@/types'
import type {
  CompetitionWorkItem,
  CompetitionWorkItemInput,
  WorkloadAssessment,
  WorkloadAssessmentDraftInput,
  WorkloadObjection,
  WorkloadObjectionInput,
  WorkloadObjectionResolutionInput,
} from '@/types/workload'

const {
  getMock,
  postMock,
  patchMock,
  delMock,
} = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
  delMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: postMock,
  patch: patchMock,
  del: delMock,
}))

import {
  createCompetitionWorkItem,
  createWorkloadObjection,
  deleteCompetitionWorkItem,
  getCompetitionWorkItems,
  getWorkloadAssessments,
  getWorkloadObjections,
  publishWorkloadAssessment,
  resolveWorkloadObjection,
  saveWorkloadAssessmentDraft,
  updateCompetitionWorkItem,
} from '@/api/workloads'

function page<T>(results: T[]): PaginatedResponse<T> {
  return {
    count: results.length,
    next: null,
    previous: null,
    results,
  }
}

function workItem(id: number): CompetitionWorkItem {
  return {
    id,
    competition: 31,
    event_name: '全国创新赛',
    event_edition: '2026 届',
    entry_name: '数字治理项目参赛队',
    project: 7,
    project_name: '数字治理项目',
    assignee: 8,
    assignee_name: '成员甲',
    collaborators: [],
    collaborator_names: [],
    reviewer: null,
    reviewer_name: '',
    title: `任务 ${id}`,
    description: '完成答辩材料',
    deadline: '2026-08-15T12:00:00+08:00',
    priority: 'medium',
    status: 'doing',
    status_display: '进行中',
    completed_at: null,
    completion_note: '',
    reference_note: '参考往届省赛材料',
    subtasks: [],
    created_by_name: '负责人甲',
    can_manage: true,
    can_edit: true,
    can_review: true,
    created_at: '2026-07-29T08:00:00+08:00',
    updated_at: '2026-07-29T08:00:00+08:00',
  }
}

function assessment(id: number): WorkloadAssessment {
  return {
    id,
    competition: 31,
    project: 7,
    project_name: '数字治理项目',
    event_name: '全国创新赛',
    event_edition: '2026 届',
    entry_name: '数字治理项目参赛队',
    version: 1,
    status: 'draft',
    status_display: '草稿',
    decision_note: '按交付物质量与实际贡献评定',
    decided_by_name: '负责人甲',
    published_at: null,
    is_current: true,
    allocations: [
      {
        id: 61,
        user: 8,
        user_name: '成员甲',
        percentage: '60.00',
        rationale: '完成核心材料',
      },
      {
        id: 62,
        user: 9,
        user_name: '成员乙',
        percentage: '40.00',
        rationale: '完成数据整理',
      },
    ],
    allocation_total: '100.00',
    objection_count: 0,
    can_manage: true,
    can_object: false,
  }
}

function objection(id: number): WorkloadObjection {
  return {
    id,
    allocation: 61,
    assessment: 51,
    competition: 31,
    allocation_user: 8,
    allocation_user_name: '成员甲',
    raised_by: 8,
    raised_by_name: '成员甲',
    reason: '核心交付物贡献未完整体现',
    status: 'open',
    status_display: '待处理',
    response: '',
    resolved_by_name: '',
    created_at: '2026-07-29T09:00:00+08:00',
    resolved_at: null,
    can_resolve: true,
  }
}

beforeEach(() => {
  getMock.mockReset()
  postMock.mockReset()
  patchMock.mockReset()
  delMock.mockReset()
})

describe('competition work item API contract', () => {
  it('uses the exact competition query and normalizes array and paginated responses', async () => {
    const arrayItem = workItem(1)
    const paginatedItem = workItem(2)
    getMock
      .mockResolvedValueOnce([arrayItem])
      .mockResolvedValueOnce(page([paginatedItem]))

    await expect(getCompetitionWorkItems({
      competition: 31,
      mine: 1,
    })).resolves.toEqual([arrayItem])
    await expect(getCompetitionWorkItems({
      competition: 31,
    })).resolves.toEqual([paginatedItem])

    expect(getMock).toHaveBeenNthCalledWith(
      1,
      '/members/competition-work-items/',
      { competition: 31, mine: 1 },
    )
    expect(getMock).toHaveBeenNthCalledWith(
      2,
      '/members/competition-work-items/',
      { competition: 31 },
    )
  })

  it('uses exact create, update and delete paths and payloads', async () => {
    const createInput: CompetitionWorkItemInput = {
      competition: 31,
      assignee: 8,
      title: '完成答辩稿',
      description: '整理并确认最终答辩版本',
      deadline: '2026-08-15T12:00:00+08:00',
      reference_note: '参考往届省赛答辩稿',
      status: 'doing',
    }
    const updateInput: Partial<CompetitionWorkItemInput> = {
      status: 'done',
      reference_note: '答辩稿已由负责人确认',
    }
    const created = workItem(11)
    const updated = {
      ...created,
      status: 'done',
      status_display: '已完成',
    }
    postMock.mockResolvedValueOnce(created)
    patchMock.mockResolvedValueOnce(updated)
    delMock.mockResolvedValueOnce(undefined)

    await expect(createCompetitionWorkItem(createInput)).resolves.toBe(created)
    await expect(updateCompetitionWorkItem(11, updateInput)).resolves.toBe(updated)
    await expect(deleteCompetitionWorkItem(11)).resolves.toBeUndefined()

    expect(postMock).toHaveBeenCalledWith(
      '/members/competition-work-items/',
      createInput,
    )
    expect(patchMock).toHaveBeenCalledWith(
      '/members/competition-work-items/11/',
      updateInput,
    )
    expect(delMock).toHaveBeenCalledWith(
      '/members/competition-work-items/11/',
    )
  })
})

describe('workload assessment API contract', () => {
  it('uses the exact competition query and normalizes array and paginated responses', async () => {
    const arrayAssessment = assessment(51)
    const paginatedAssessment = assessment(52)
    getMock
      .mockResolvedValueOnce([arrayAssessment])
      .mockResolvedValueOnce(page([paginatedAssessment]))

    await expect(getWorkloadAssessments(31)).resolves.toEqual([arrayAssessment])
    await expect(getWorkloadAssessments(32)).resolves.toEqual([paginatedAssessment])

    expect(getMock).toHaveBeenNthCalledWith(
      1,
      '/members/workload-assessments/',
      { competition: 31 },
    )
    expect(getMock).toHaveBeenNthCalledWith(
      2,
      '/members/workload-assessments/',
      { competition: 32 },
    )
  })

  it('uses exact draft and publish action paths and payloads', async () => {
    const draftInput: WorkloadAssessmentDraftInput = {
      competition: 31,
      decision_note: '按交付物质量与实际贡献评定',
      allocations: [
        {
          user: 8,
          percentage: 60,
          rationale: '完成核心材料',
        },
        {
          user: 9,
          percentage: 40,
          rationale: '完成数据整理',
        },
      ],
    }
    const draft = assessment(51)
    const published = {
      ...draft,
      status: 'published',
      status_display: '已发布',
      published_at: '2026-07-29T10:00:00+08:00',
    }
    postMock
      .mockResolvedValueOnce(draft)
      .mockResolvedValueOnce(published)

    await expect(saveWorkloadAssessmentDraft(draftInput)).resolves.toBe(draft)
    await expect(publishWorkloadAssessment(51)).resolves.toBe(published)

    expect(postMock).toHaveBeenNthCalledWith(
      1,
      '/members/workload-assessments/save-draft/',
      draftInput,
    )
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      '/members/workload-assessments/51/publish/',
    )
  })
})

describe('workload objection API contract', () => {
  it('uses the exact competition query and normalizes array and paginated responses', async () => {
    const arrayObjection = objection(71)
    const paginatedObjection = objection(72)
    getMock
      .mockResolvedValueOnce([arrayObjection])
      .mockResolvedValueOnce(page([paginatedObjection]))

    await expect(getWorkloadObjections(31)).resolves.toEqual([arrayObjection])
    await expect(getWorkloadObjections(32)).resolves.toEqual([paginatedObjection])

    expect(getMock).toHaveBeenNthCalledWith(
      1,
      '/members/workload-objections/',
      { competition: 31 },
    )
    expect(getMock).toHaveBeenNthCalledWith(
      2,
      '/members/workload-objections/',
      { competition: 32 },
    )
  })

  it('uses exact create and resolve action paths and payloads', async () => {
    const createInput: WorkloadObjectionInput = {
      allocation: 61,
      reason: '核心交付物贡献未完整体现',
    }
    const resolutionInput: WorkloadObjectionResolutionInput = {
      status: 'resolved',
      response: '已核对交付物并在新版本中调整占比',
    }
    const created = objection(71)
    const resolved = {
      ...created,
      status: 'resolved',
      status_display: '已解决',
      response: resolutionInput.response,
      resolved_by_name: '负责人乙',
      resolved_at: '2026-07-29T11:00:00+08:00',
    }
    postMock
      .mockResolvedValueOnce(created)
      .mockResolvedValueOnce(resolved)

    await expect(createWorkloadObjection(createInput)).resolves.toBe(created)
    await expect(resolveWorkloadObjection(71, resolutionInput)).resolves.toBe(resolved)

    expect(postMock).toHaveBeenNthCalledWith(
      1,
      '/members/workload-objections/',
      createInput,
    )
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      '/members/workload-objections/71/resolve/',
      resolutionInput,
    )
  })
})
