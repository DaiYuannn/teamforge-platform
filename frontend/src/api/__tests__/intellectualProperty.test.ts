import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/api/request', () => ({ default: requestMock }))

import {
  addIPCandidate,
  confirmIPContributor,
  createIPObjection,
  deleteIPCandidate,
  getIPCandidates,
  reviewIPObjection,
  updateIPCandidate,
  updateIPApplication,
  updateIPMaterial,
  uploadIPFinalCertificate,
  uploadIPMaterial,
} from '@/api/intellectualProperty'

describe('intellectual-property API contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sends material uploads through the multipart material_upload contract', async () => {
    const formData = new FormData()
    const file = new File(['content'], 'material.pdf', { type: 'application/pdf' })
    formData.append('material_upload', file)

    await uploadIPMaterial(12, formData)

    expect(formData.get('application')).toBe('12')
    expect(formData.get('material_upload')).toBe(file)
    expect(requestMock.post).toHaveBeenCalledWith(
      '/intellectual-property/materials/',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  })

  it('uses the application-scoped candidate list contract', async () => {
    const candidate = {
      user: 8,
      legal_role: 'inventor' as const,
      planned_order: 1,
      status: 'confirmed' as const,
      identity_check_status: 'matched' as const,
      note: '实名信息一致',
    }

    await getIPCandidates(18)
    await addIPCandidate(18, candidate)
    await updateIPCandidate(18, 5, {
      planned_order: 2,
      status: 'submitted',
    })
    await deleteIPCandidate(18, 5)

    expect(requestMock.get).toHaveBeenCalledWith(
      '/intellectual-property/applications/18/candidates/',
    )
    expect(requestMock.post).toHaveBeenCalledWith(
      '/intellectual-property/applications/18/candidates/',
      candidate,
    )
    expect(requestMock.patch).toHaveBeenCalledWith(
      '/intellectual-property/applications/18/candidates/',
      {
        candidate_id: 5,
        planned_order: 2,
        status: 'submitted',
      },
    )
    expect(requestMock.delete).toHaveBeenCalledWith(
      '/intellectual-property/applications/18/candidates/',
      { params: { candidate_id: 5 } },
    )
  })

  it('sends objection proof files through proof_upload', async () => {
    const formData = new FormData()
    const file = new File(['proof'], 'proof.png', { type: 'image/png' })
    formData.append('objection_type', 'ranking')
    formData.append('content', '排序依据需要复核')
    formData.append('proof_upload', file)

    await createIPObjection(9, formData)

    expect(formData.get('application')).toBe('9')
    expect(formData.get('proof_upload')).toBe(file)
    expect(requestMock.post).toHaveBeenCalledWith(
      '/intellectual-property/objections/',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  })

  it('uses the dedicated contributor confirmation action', async () => {
    await confirmIPContributor(18)

    expect(requestMock.post).toHaveBeenCalledWith('/intellectual-property/contributors/18/confirm/')
  })

  it('forwards the teacher review action and final status unchanged', async () => {
    const payload = {
      action: 'teacher_confirm' as const,
      teacher_opinion: '同意负责人意见',
      final_result: '按现有贡献记录执行',
      final_status: 'resolved' as const,
    }

    await reviewIPObjection(5, payload)

    expect(requestMock.patch).toHaveBeenCalledWith(
      '/intellectual-property/objections/5/review/',
      payload,
    )
  })

  it('includes application_code in application updates', async () => {
    const payload = { application_code: 'IP-2026-018', title: '更新后的成果名称' }

    await updateIPApplication(18, payload)

    expect(requestMock.patch).toHaveBeenCalledWith(
      '/intellectual-property/applications/18/',
      payload,
    )
  })

  it('uploads the final certificate through the guarded multipart field', async () => {
    const file = new File(['certificate'], 'certificate.pdf', {
      type: 'application/pdf',
    })

    await uploadIPFinalCertificate(18, file)

    const payload = requestMock.patch.mock.calls[0][1] as FormData
    expect(payload.get('final_certificate_upload')).toBe(file)
    expect(requestMock.patch).toHaveBeenCalledWith(
      '/intellectual-property/applications/18/',
      payload,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  })

  it('updates the final flag on an existing material version', async () => {
    await updateIPMaterial(33, { is_final: true })

    expect(requestMock.patch).toHaveBeenCalledWith(
      '/intellectual-property/materials/33/',
      { is_final: true },
    )
  })
})
