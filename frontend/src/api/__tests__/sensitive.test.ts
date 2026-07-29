import { beforeEach, describe, expect, it, vi } from 'vitest'

const { downloadMock, getMock, postMock, uploadMock } = vi.hoisted(() => ({
  downloadMock: vi.fn(),
  getMock: vi.fn(),
  postMock: vi.fn(),
  uploadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  download: downloadMock,
  get: getMock,
  post: postMock,
  upload: uploadMock,
}))

import {
  createSensitiveData,
  downloadSensitiveAttachmentByGrant,
  downloadSensitiveAttachment,
  getAccessRequest,
  getMyAccessRequests,
  getPendingApproveRequests,
  getSensitiveData,
  getSensitiveDataGrants,
  getSensitiveGrantAccessLogs,
  getSensitiveGrantCandidates,
  revokeSensitiveDataGrant,
  saveSensitiveDataGrant,
  viewSensitiveData,
} from '@/api/sensitive'

beforeEach(() => {
  downloadMock.mockReset()
  getMock.mockReset()
  postMock.mockReset()
  uploadMock.mockReset()
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

  it('uses multipart only when a direct attachment is supplied', async () => {
    const attachment = new File(['plan'], 'plan.pdf', { type: 'application/pdf' })
    await createSensitiveData({
      data_type: 'other',
      title: '团队计划书',
      team: 3,
      attachment_upload: attachment,
    })

    expect(uploadMock).toHaveBeenCalledWith('/sensitive/data/', expect.any(FormData))
    const formData = uploadMock.mock.calls[0]?.[1] as FormData
    expect(formData.get('title')).toBe('团队计划书')
    expect(formData.get('team')).toBe('3')
    expect(formData.get('attachment_upload')).toBe(attachment)
    expect(postMock).not.toHaveBeenCalled()
  })

  it('uses record-bound grant, candidate, audit, view and download endpoints', async () => {
    const expiresAt = '2026-07-30T10:00:00+08:00'
    getMock.mockResolvedValue([])
    postMock.mockResolvedValue({ id: 9 })
    downloadMock.mockResolvedValue(new Blob(['sensitive']))

    await getSensitiveDataGrants(5)
    await getSensitiveGrantCandidates(5, 'LYC')
    await getSensitiveGrantAccessLogs(5)
    await saveSensitiveDataGrant(5, {
      granted_to: 7,
      can_view: true,
      can_download: true,
      purpose: '提交专利',
      expires_at: expiresAt,
    })
    await viewSensitiveData(5, undefined, 9)
    await downloadSensitiveAttachmentByGrant(5, 9)
    await revokeSensitiveDataGrant(5, 9)

    expect(getMock).toHaveBeenCalledWith('/sensitive/data/5/grants/')
    expect(getMock).toHaveBeenCalledWith('/sensitive/data/5/grant-candidates/', {
      search: 'LYC',
    })
    expect(getMock).toHaveBeenCalledWith('/sensitive/data/5/grant-access-logs/')
    expect(postMock).toHaveBeenCalledWith('/sensitive/data/5/grants/', {
      granted_to: 7,
      can_view: true,
      can_download: true,
      purpose: '提交专利',
      expires_at: expiresAt,
    })
    expect(postMock).toHaveBeenCalledWith('/sensitive/data/5/view/', { grant_id: 9 })
    expect(downloadMock).toHaveBeenCalledWith(
      '/sensitive/data/5/download-by-grant/',
      { params: { grant_id: 9 } },
    )
    expect(postMock).toHaveBeenCalledWith('/sensitive/data/5/grants/9/revoke/')
  })
})
