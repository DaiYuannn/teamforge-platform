import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const detailSource = readFileSync(
  resolve(process.cwd(), 'src/views/projects/ProjectDetailView.vue'),
  'utf8',
)
const listSource = readFileSync(
  resolve(process.cwd(), 'src/views/projects/ProjectListView.vue'),
  'utf8',
)

describe('project information closure', () => {
  it('keeps project summary fields visible with a created-at update fallback', () => {
    for (const field of [
      'member_count',
      'task_count',
      'competition_count',
      'finance_balance',
    ]) {
      expect(listSource).toContain(field)
    }
    expect(listSource).toContain('row.last_leader_update || row.created_at')
    expect(listSource).toContain('item.last_leader_update || item.created_at')
  })

  it('connects every project operation area to a filtered real page', () => {
    expect(detailSource).toContain("path: '/tasks'")
    expect(detailSource).toContain("task_id: String(taskId)")
    expect(detailSource).toContain("path: '/competitions'")
    expect(detailSource).toContain("path: '/finance'")
    expect(detailSource).toContain("path: '/contributions'")
    expect(detailSource).toContain("path: '/contributions/pending'")
    expect(detailSource).toContain("path: '/intellectual-property'")
    expect(detailSource).toContain("path: '/audit/logs'")
    expect(detailSource).toContain("search: `/projects/${projectId}/`")
  })

  it('loads project budget and applies workflow permissions to local actions', () => {
    expect(detailSource).toContain('getFinanceBudgetByProject(projectId)')
    expect(detailSource).toContain('budget.total_income')
    expect(detailSource).toContain(':show-actions="canManageProjectWorkflow"')
    expect(detailSource).toContain('v-if="canManageProjectWorkflow"')
    expect(detailSource).toContain(':can-change-status="canChangeTaskStatus"')
    expect(detailSource).toContain(':can-change-to-status="canChangeTaskToStatus"')
    expect(detailSource).toContain(
      'changeTaskStatus(task.id, newStatus, delayReason, completionNote)',
    )
  })

  it('removes every finance surface for external collaborators', () => {
    for (const source of [listSource, detailSource]) {
      expect(source).toContain(
        "userStore.userInfo?.membership_status === 'external'",
      )
      expect(source).toContain('!isExternalCollaborator')
    }
    expect(listSource).toContain(
      'v-if="!isExternalCollaborator"\n            label="经费余额"',
    )
    expect(listSource).toContain(
      '<div v-if="!isExternalCollaborator">\n              <dt>经费余额</dt>',
    )
    expect(listSource).toContain(
      'v-if="!isExternalCollaborator"\n          :icon="Download"',
    )
    expect(detailSource).toContain(
      '<el-tab-pane v-if="!isExternalCollaborator" label="经费" name="finance">',
    )
    expect(detailSource).toContain(
      "{ name: 'finance', label: '经费', icon: Wallet, internalOnly: true }",
    )
    expect(detailSource).toContain(
      '(!item.internalOnly || !isExternalCollaborator)',
    )
  })
})
