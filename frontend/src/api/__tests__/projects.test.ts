import { beforeEach, describe, expect, it, vi } from 'vitest'

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: postMock,
  patch: vi.fn(),
  del: vi.fn(),
}))

import { advanceStage, leaderUpdate } from '@/api/projects'

beforeEach(() => {
  postMock.mockReset()
  postMock.mockResolvedValue({})
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
