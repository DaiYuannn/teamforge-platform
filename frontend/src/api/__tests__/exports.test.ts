import { beforeEach, describe, expect, it, vi } from 'vitest'

const { downloadMock } = vi.hoisted(() => ({ downloadMock: vi.fn() }))

vi.mock('@/api/request', () => ({
  download: downloadMock,
}))

import { exportData, exportProjectReport } from '@/api/exports'

beforeEach(() => downloadMock.mockReset())

describe('task export filters', () => {
  it('passes the active task-list filters to the existing export endpoint', async () => {
    const blob = new Blob(['tasks'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(exportData('tasks', 'xlsx', 24, undefined, {
      search: '答辩材料',
      status: 'pending_review',
      priority: 'high',
      assignee: 11,
      scope: 'mine',
    })).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith('/exports/', {
      params: {
        type: 'tasks',
        file_format: 'xlsx',
        project_id: 24,
        ip_id: undefined,
        search: '答辩材料',
        status: 'pending_review',
        priority: 'high',
        assignee: 11,
        scope: 'mine',
      },
    })
  })

  it('returns the project report as a Blob', async () => {
    const blob = new Blob(['project report'])
    downloadMock.mockResolvedValueOnce(blob)

    await expect(exportProjectReport(24)).resolves.toBe(blob)

    expect(downloadMock).toHaveBeenCalledWith('/exports/project-report/24/')
  })
})
