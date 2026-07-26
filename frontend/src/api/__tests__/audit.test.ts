import { beforeEach, describe, expect, it, vi } from 'vitest'

const { downloadMock } = vi.hoisted(() => ({
  downloadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  default: { get: vi.fn() },
  download: downloadMock,
}))

import { exportOperationLogs } from '@/api/audit'

beforeEach(() => {
  downloadMock.mockReset()
})

describe('operation log export API contract', () => {
  it('exports the same filters used by the audit list', async () => {
    downloadMock.mockResolvedValueOnce(new Blob(['audit']))
    const params = {
      search: '/projects/17/',
      module: 'files',
      operation_type: 'download',
      start_date: '2026-07-01',
      end_date: '2026-07-31',
    }

    await exportOperationLogs(params)

    expect(downloadMock).toHaveBeenCalledWith(
      '/audit/operation-logs/export/',
      { params },
    )
  })
})
