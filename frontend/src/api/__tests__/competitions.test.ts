import { beforeEach, describe, expect, it, vi } from 'vitest'

const { downloadMock } = vi.hoisted(() => ({
  downloadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
  download: downloadMock,
}))

import { exportCompetitions } from '@/api/competitions'

beforeEach(() => {
  downloadMock.mockReset()
})

describe('competition export API contract', () => {
  it('exports the complete current list filter without pagination', async () => {
    const blob = new Blob(['competition'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(exportCompetitions({
      search: '挑战杯',
      project: 23,
      level: 'province',
      status: 'ongoing',
    })).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith('/exports/', {
      params: {
        type: 'competitions',
        file_format: 'xlsx',
        search: '挑战杯',
        project_id: 23,
        level: 'province',
        status: 'ongoing',
      },
    })
  })
})
