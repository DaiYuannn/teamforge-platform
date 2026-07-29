import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('dashboard effective workload entry', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/views/dashboard/DashboardView.vue'),
    'utf8',
  )

  it('links to the competition workload workspace without loading legacy schedules', () => {
    expect(source).toContain('label="有效工作量"')
    expect(source).toContain('进入团队有效工作量')
    expect(source).toContain("goTo('/members/team-schedule')")
    expect(source).not.toContain('getAllLatestSchedules')
    expect(source).not.toContain('available_hours')
    expect(source).not.toContain('work_hours')
  })
})
