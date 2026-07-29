import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('workflow approval todo presentation', () => {
  const todoSource = readFileSync(
    resolve(process.cwd(), 'src/views/todo/TodoListView.vue'),
    'utf8',
  )
  const dashboardSource = readFileSync(
    resolve(process.cwd(), 'src/views/dashboard/DashboardView.vue'),
    'utf8',
  )

  it('provides a Chinese label, icon, tone, and explicit filter', () => {
    expect(todoSource).toContain('value="workflow_approval"')
    expect(todoSource).toContain("workflow_approval: '流程审批'")
    expect(todoSource).toContain('workflow_approval: Stamp')
    expect(todoSource).toContain("workflow_approval: 'warning'")
  })

  it('includes workflow approvals in the dashboard approval count', () => {
    expect(dashboardSource).toContain("workflow_approval: '流程审批'")
    expect(dashboardSource).toContain(
      "['approval', 'workflow_approval', 'contribution_review'",
    )
    expect(dashboardSource).toContain(
      "['approval', 'workflow_approval', 'ip_todo', 'finance_review']",
    )
  })
})
