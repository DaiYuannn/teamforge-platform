import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))

vi.mock('@/api/request', () => ({ ...mocks, download: vi.fn() }))

import { getWeeklyReport, setDefaultDashboard } from '@/api/analytics'
import { generateCustomReport, updateCustomReport } from '@/api/reports'

beforeEach(() => Object.values(mocks).forEach((mock) => mock.mockReset()))

describe('analytics studio API contract', () => {
  it('loads scoped weekly analysis and sets a default dashboard', async () => {
    await getWeeklyReport({ project_id: 8, weeks: 2 })
    await setDefaultDashboard(4)

    expect(mocks.get).toHaveBeenCalledWith('/dashboard/weekly-report/', {
      project_id: 8,
      weeks: 2,
    })
    expect(mocks.post).toHaveBeenCalledWith('/dashboard/custom/4/set_default/')
  })

  it('updates and generates an independent custom report', async () => {
    await updateCustomReport(6, { name: '项目状态月报' })
    await generateCustomReport(6)

    expect(mocks.patch).toHaveBeenCalledWith('/exports/custom-reports/6/', {
      name: '项目状态月报',
    })
    expect(mocks.post).toHaveBeenCalledWith('/exports/custom-reports/6/generate/')
  })
})
