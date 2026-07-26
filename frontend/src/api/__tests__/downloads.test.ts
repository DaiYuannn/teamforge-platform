import { beforeEach, describe, expect, it, vi } from 'vitest'

const { downloadMock } = vi.hoisted(() => ({
  downloadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  del: vi.fn(),
  download: downloadMock,
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}))

import { downloadDemoBackup } from '@/api/backup'
import { downloadReportExecution } from '@/api/reports'

beforeEach(() => {
  downloadMock.mockReset()
})

describe('generated file download API contracts', () => {
  it('returns a demo backup ZIP as a Blob', async () => {
    const blob = new Blob(['backup'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(downloadDemoBackup('demo-backup-1')).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith('/common/backup/demo-backup-1/download/')
  })

  it('returns a scheduled report execution as a Blob', async () => {
    const blob = new Blob(['report'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(downloadReportExecution(12, 34)).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith(
      '/exports/scheduled-reports/12/executions/34/download/',
    )
  })
})
