import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))

import { getMembers } from '@/api/members'

beforeEach(() => {
  vi.clearAllMocks()
  getMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
})

describe('member directory query API', () => {
  it('passes the selected team identity together with existing filters', async () => {
    await getMembers({
      page: 1,
      page_size: 20,
      team: 9,
      team_role: 'co_lead',
      school: '示例大学',
      membership_status: 'active',
    })

    expect(getMock).toHaveBeenCalledWith('/members/', {
      page: 1,
      page_size: 20,
      team: 9,
      team_role: 'co_lead',
      school: '示例大学',
      membership_status: 'active',
    })
  })
})
