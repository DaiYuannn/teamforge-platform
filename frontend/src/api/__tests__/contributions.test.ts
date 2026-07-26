import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PaginatedResponse } from '@/types'

const { getMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  get: getMock,
}))

import { getMyContributions, getPendingReview } from '@/api/contributions'

beforeEach(() => {
  getMock.mockReset()
  getMock.mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  } satisfies PaginatedResponse<never>)
})

describe('project-scoped contribution deep links', () => {
  it('keeps the project filter while loading my contributions', async () => {
    await getMyContributions({ project: 17 })

    expect(getMock).toHaveBeenCalledWith(
      '/contributions/contributions/my_contributions/',
      { project: 17, page: 1, page_size: 100 },
    )
  })

  it('keeps the project filter while loading pending reviews', async () => {
    await getPendingReview({ project: 17 })

    expect(getMock).toHaveBeenCalledWith(
      '/contributions/contributions/pending_review/',
      { project: 17, page: 1, page_size: 100 },
    )
  })
})
