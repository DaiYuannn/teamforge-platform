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
  uploadFile,
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

  it('keeps the selected folder in the upload form data', async () => {
    uploadMock.mockResolvedValue({ id: 12, folder: 3 })
    const file = new File(['folder-linked'], '计划书.txt', { type: 'text/plain' })

    await uploadFile(8, file, {
      project: 8,
      folder: 3,
      level: 'internal',
      description: '上传到当前目录',
    })

    expect(uploadMock).toHaveBeenCalledWith('/files/', expect.any(FormData))
    const formData = uploadMock.mock.calls[0]?.[1] as FormData
    expect(formData.get('project')).toBe('8')
    expect(formData.get('folder')).toBe('3')
    expect(formData.get('level')).toBe('internal')
    expect(formData.get('file')).toBe(file)
  })

  it('sends exactly one selected small-team or competition-entry scope', async () => {
    uploadMock.mockResolvedValue({ id: 13 })
    const teamFile = new File(['team'], 'team.txt', { type: 'text/plain' })
    const competitionFile = new File(['competition'], 'competition.txt', {
      type: 'text/plain',
    })

    await uploadFile(8, teamFile, {
      project: 8,
      level: 'internal',
      team: 21,
    })
    await uploadFile(8, competitionFile, {
      project: 8,
      level: 'internal',
      competition_entry: 34,
    })

    const teamForm = uploadMock.mock.calls[0]?.[1] as FormData
    const competitionForm = uploadMock.mock.calls[1]?.[1] as FormData
    expect(teamForm.get('team')).toBe('21')
    expect(teamForm.get('competition_entry')).toBeNull()
    expect(competitionForm.get('competition_entry')).toBe('34')
    expect(competitionForm.get('team')).toBeNull()
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
