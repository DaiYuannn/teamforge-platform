import { beforeEach, describe, expect, it, vi } from 'vitest'

const { uploadMock } = vi.hoisted(() => ({
  uploadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  download: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
  upload: uploadMock,
}))

import { previewMaterialArchive } from '@/api/imports'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('material archive import API', () => {
  it('uploads a ZIP and its exact target team to the guarded preview endpoint', async () => {
    const archive = new File(['zip'], 'materials.zip', { type: 'application/zip' })

    await previewMaterialArchive(archive, 12)

    expect(uploadMock).toHaveBeenCalledWith(
      '/imports/tasks/preview-materials/',
      expect.any(FormData),
    )
    const formData = uploadMock.mock.calls[0]?.[1] as FormData
    expect(formData.get('file')).toBe(archive)
    expect(formData.get('team')).toBe('12')
  })
})
