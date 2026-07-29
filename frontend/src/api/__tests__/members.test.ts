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

import { getMembers, normalizeMemberQueryParams } from '@/api/members'

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

  it('keeps free-text fragments and their case while trimming empty filters', async () => {
    await getMembers({
      page: 1,
      page_size: 20,
      search: '  LYC  ',
      grade: ' 2024 ',
      school: ' 示例 ',
      major: ' 计算机 ',
      team_role: undefined,
      membership_status: '',
    })

    expect(getMock).toHaveBeenCalledWith('/members/', {
      page: 1,
      page_size: 20,
      search: 'LYC',
      grade: '2024',
      school: '示例',
      major: '计算机',
    })
  })

  it('does not lowercase or convert fragment queries into exact-match values', () => {
    expect(normalizeMemberQueryParams({
      search: 'ZhangSan',
      school: 'University',
      major: 'Computer',
    })).toEqual({
      search: 'ZhangSan',
      school: 'University',
      major: 'Computer',
    })
  })
})
