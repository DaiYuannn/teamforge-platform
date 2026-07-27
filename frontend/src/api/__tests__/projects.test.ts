import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getMock, postMock, patchMock, delMock } = vi.hoisted(() => ({
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
  advanceStage,
  approveProjectReview,
  getMaterialCheck,
  getProjectHealthScore,
  getRiskPrediction,
  getSmartReview,
  instantiateProjectTemplate,
  leaderUpdate,
  replyDiscussionTopic,
  resolveProjectRisk,
  toggleDiscussionClose,
  toggleDiscussionPin,
  toggleMilestone,
  updateKnowledgeArticle,
} from '@/api/projects'

beforeEach(() => {
  postMock.mockReset()
  getMock.mockReset()
  patchMock.mockReset()
  delMock.mockReset()
  postMock.mockResolvedValue({})
})

describe('project collaboration API contract', () => {
  it('uses explicit action endpoints for workflow operations', async () => {
    await toggleMilestone(3)
    await resolveProjectRisk(4)
    await replyDiscussionTopic(5, { content: '同意这个方案' })
    await toggleDiscussionPin(5)
    await toggleDiscussionClose(5)
    await approveProjectReview(6)

    expect(postMock).toHaveBeenNthCalledWith(1, '/projects/milestones/3/toggle/')
    expect(postMock).toHaveBeenNthCalledWith(2, '/projects/risks/4/resolve/')
    expect(postMock).toHaveBeenNthCalledWith(3, '/projects/discussions/5/reply/', {
      content: '同意这个方案',
    })
    expect(postMock).toHaveBeenNthCalledWith(4, '/projects/discussions/5/toggle-pin/')
    expect(postMock).toHaveBeenNthCalledWith(5, '/projects/discussions/5/toggle-close/')
    expect(postMock).toHaveBeenNthCalledWith(6, '/projects/reviews/6/approve/')
  })

  it('requests all four insights with a project_id query', async () => {
    getMock.mockResolvedValue({})

    await Promise.all([
      getRiskPrediction(19),
      getProjectHealthScore(19),
      getSmartReview(19),
      getMaterialCheck(19),
    ])

    expect(getMock).toHaveBeenNthCalledWith(1, '/projects/risk-prediction/', { project_id: 19 })
    expect(getMock).toHaveBeenNthCalledWith(2, '/projects/health-score/', { project_id: 19 })
    expect(getMock).toHaveBeenNthCalledWith(3, '/projects/smart-review/', { project_id: 19 })
    expect(getMock).toHaveBeenNthCalledWith(4, '/projects/material-check/', { project_id: 19 })
  })

  it('preserves template instantiation and knowledge update payloads', async () => {
    patchMock.mockResolvedValue({})
    await instantiateProjectTemplate(7, {
      name: '新项目',
      code: 'NEW-01',
      leader: 2,
      start_date: null,
      planned_end_date: null,
    })
    await updateKnowledgeArticle(8, { title: '交付指南' })

    expect(postMock).toHaveBeenLastCalledWith('/projects/templates/7/instantiate/', {
      name: '新项目',
      code: 'NEW-01',
      leader: 2,
      start_date: null,
      planned_end_date: null,
    })
    expect(patchMock).toHaveBeenCalledWith('/projects/knowledge/8/', { title: '交付指南' })
  })
})

describe('project workflow API contract', () => {
  it('sends the selected stage and audit note to the stage action', async () => {
    await advanceStage(23, { target_stage: 8, remark: '材料已复核，进入答辩准备' })

    expect(postMock).toHaveBeenCalledWith('/projects/23/stage/', {
      to_stage: 8,
      note: '材料已复核，进入答辩准备',
    })
  })

  it('sends the progress description to the leader update action', async () => {
    await leaderUpdate(23, '本周期完成了样机联调与材料复核')

    expect(postMock).toHaveBeenCalledWith('/projects/23/leader_update/', {
      note: '本周期完成了样机联调与材料复核',
    })
  })
})
