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

import { getTeamMembers } from '@/api/teams'

beforeEach(() => {
  vi.clearAllMocks()
  getMock.mockResolvedValue([])
})

describe('team member query API', () => {
  it('keeps the backend default order when no filter is active', async () => {
    await getTeamMembers(7)

    expect(getMock).toHaveBeenCalledWith('/teams/7/members/', undefined)
  })

  it('passes identity, school and status filters to the backend', async () => {
    await getTeamMembers(7, {
      role: 'co_lead',
      school: '示例大学',
      status: 'active',
    })

    expect(getMock).toHaveBeenCalledWith('/teams/7/members/', {
      role: 'co_lead',
      school: '示例大学',
      status: 'active',
    })
  })
})
