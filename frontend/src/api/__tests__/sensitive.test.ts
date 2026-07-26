import { beforeEach, describe, expect, it, vi } from 'vitest'

const { downloadMock, getMock, postMock } = vi.hoisted(() => ({
  downloadMock: vi.fn(),
  getMock: vi.fn(),
  postMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  download: downloadMock,
  get: getMock,
  post: postMock,
}))

import {
  downloadSensitiveAttachment,
  getSensitiveData,
} from '@/api/sensitive'

beforeEach(() => {
  downloadMock.mockReset()
  getMock.mockReset()
  postMock.mockReset()
})

describe('sensitive attachment API contract', () => {
  it('loads the masked team catalogue with ordinary query parameters', async () => {
    getMock.mockResolvedValueOnce({ count: 0, results: [] })

    await getSensitiveData({ page: 1, page_size: 100 })

    expect(getMock).toHaveBeenCalledWith('/sensitive/data/', {
      page: 1,
      page_size: 100,
    })
  })

  it('uses the approved-request attachment endpoint for applicants', async () => {
    const blob = new Blob(['attachment'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(downloadSensitiveAttachment(17)).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith(
      '/sensitive/requests/17/download-attachment/',
    )
  })
})
