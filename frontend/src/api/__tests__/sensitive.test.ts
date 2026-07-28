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
  createSensitiveData,
  downloadSensitiveAttachment,
  getAccessRequest,
  getMyAccessRequests,
  getPendingApproveRequests,
  getSensitiveData,
} from '@/api/sensitive'

beforeEach(() => {
  downloadMock.mockReset()
  getMock.mockReset()
  postMock.mockReset()
})

describe('sensitive attachment API contract', () => {
  it('submits new plaintext only to the guarded sensitive-data create endpoint', async () => {
    const payload = {
      data_type: 'id_card',
      title: '成员身份证号',
      plaintext: '110101199001011234',
      subject_user: 7,
      team: 3,
    }

    await createSensitiveData(payload)

    expect(postMock).toHaveBeenCalledWith('/sensitive/data/', payload)
  })

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

  it('supports paginating personal requests and the approval queue', async () => {
    getMock.mockResolvedValue({ count: 0, results: [] })

    await getMyAccessRequests({ page: 2, page_size: 10 })
    await getPendingApproveRequests({ page: 3, page_size: 20 })

    expect(getMock).toHaveBeenNthCalledWith(
      1,
      '/sensitive/requests/my_requests/',
      { page: 2, page_size: 10 },
    )
    expect(getMock).toHaveBeenNthCalledWith(
      2,
      '/sensitive/requests/pending_approve/',
      { page: 3, page_size: 20 },
    )
  })

  it('loads a single request for notification deep links', async () => {
    getMock.mockResolvedValueOnce({ id: 17 })

    await getAccessRequest(17)

    expect(getMock).toHaveBeenCalledWith('/sensitive/requests/17/')
  })
})
