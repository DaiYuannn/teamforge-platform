import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getMock, postMock, patchMock, delMock, uploadMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
  delMock: vi.fn(),
  uploadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: postMock,
  patch: patchMock,
  del: delMock,
  upload: uploadMock,
  download: vi.fn(),
}))

import {
  createFileFolder,
  getFile,
  getFileFolders,
  getOfficePreview,
  getRecycledFiles,
  moveFile,
  permanentlyDeleteFile,
  replaceFileTags,
  revokeFileShareLink,
} from '@/api/files'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('file management closure API', () => {
  it('loads one file for a global-search deep link', async () => {
    const file = { id: 11, name: '验收报告.pdf' }
    getMock.mockResolvedValue(file)

    await expect(getFile(11)).resolves.toEqual(file)
    expect(getMock).toHaveBeenCalledWith('/files/11/')
  })

  it('normalizes paginated folder results', async () => {
    const folder = { id: 2, project: 8, name: '终稿' }
    getMock.mockResolvedValue({ count: 1, next: null, previous: null, results: [folder] })

    await expect(getFileFolders(8)).resolves.toEqual([folder])
    expect(getMock).toHaveBeenCalledWith('/files/folders/', {
      project: 8,
      page: 1,
      page_size: 200,
    })
  })

  it('uses governed folder and move endpoints', async () => {
    postMock.mockResolvedValue({ id: 3 })

    await createFileFolder({ project: 8, name: '材料', parent: null })
    await moveFile(11, 3)

    expect(postMock).toHaveBeenNthCalledWith(1, '/files/folders/', {
      project: 8,
      name: '材料',
      parent: null,
    })
    expect(postMock).toHaveBeenNthCalledWith(2, '/files/11/move/', { folder: 3 })
  })

  it('synchronizes only changed tag relations', async () => {
    postMock.mockResolvedValue({})

    await replaceFileTags(11, [1, 2], [2, 3])

    expect(postMock).toHaveBeenCalledWith('/files/tags/assign/', {
      file: 11,
      tags: [3],
    })
    expect(postMock).toHaveBeenCalledWith('/files/tags/unassign/', {
      file: 11,
      tags: [1],
    })
  })

  it('uses explicit share, recycle and office preview endpoints', async () => {
    postMock.mockResolvedValue({})
    getMock.mockResolvedValue([])
    delMock.mockResolvedValue(undefined)

    await revokeFileShareLink(7)
    await getRecycledFiles()
    await permanentlyDeleteFile(11)
    await getOfficePreview(11)

    expect(postMock).toHaveBeenCalledWith('/files/shares/7/revoke/')
    expect(getMock).toHaveBeenCalledWith('/recycle-bin/', { type: 'file' })
    expect(delMock).toHaveBeenCalledWith('/recycle-bin/', {
      params: { type: 'file', id: 11 },
    })
    expect(getMock).toHaveBeenCalledWith('/files/11/office-preview/')
  })
})
