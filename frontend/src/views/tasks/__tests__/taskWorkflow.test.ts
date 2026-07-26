import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { Task } from '@/types'
import {
  canTransitionTaskStatus,
  getAllowedTaskStatusTargets,
  getManagerTaskStatusTargets,
  parsePositiveRouteId,
} from '../taskWorkflow'

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: 1,
    title: '闭环任务',
    description: '',
    project: 7,
    assignee: 11,
    assignee_name: '执行人',
    collaborator_ids: [12],
    reviewer: 13,
    status: 'doing',
    deadline: '2026-08-01T12:00:00Z',
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-01T12:00:00Z',
    ...overrides,
  }
}

describe('task workflow permissions', () => {
  it('lets executors and collaborators submit review but never confirm completion', () => {
    const current = task()
    expect(getAllowedTaskStatusTargets(current, 11, false)).toEqual([
      'pending_review',
      'need_help',
    ])
    expect(getAllowedTaskStatusTargets(current, 12, false)).toEqual([
      'pending_review',
      'need_help',
    ])
    expect(canTransitionTaskStatus(current, 'done', 11, false)).toBe(false)
  })

  it('lets only the reviewer role complete a pending-review task', () => {
    const current = task({ status: 'pending_review' })
    expect(getAllowedTaskStatusTargets(current, 13, false)).toEqual(['done', 'doing'])
    expect(getAllowedTaskStatusTargets(current, 11, false)).toEqual([])
  })

  it('keeps manager transitions explicit and disallows doing to done', () => {
    expect(getManagerTaskStatusTargets('doing')).toEqual([
      'pending_review',
      'overdue',
      'paused',
      'cancelled',
      'need_help',
    ])
    expect(getManagerTaskStatusTargets('doing')).not.toContain('done')
    expect(getManagerTaskStatusTargets('pending_review')).toContain('done')
  })
})

describe('task deep-link parameters', () => {
  it('accepts positive project_id/task_id values and rejects unsafe values', () => {
    expect(parsePositiveRouteId('24')).toBe(24)
    expect(parsePositiveRouteId(['31', '32'])).toBe(31)
    expect(parsePositiveRouteId('0')).toBeUndefined()
    expect(parsePositiveRouteId('-2')).toBeUndefined()
    expect(parsePositiveRouteId('1.5')).toBeUndefined()
    expect(parsePositiveRouteId('not-an-id')).toBeUndefined()
  })
})

describe('task form closure fields', () => {
  const dialogSource = readFileSync(
    resolve(process.cwd(), 'src/views/tasks/TaskFormDialog.vue'),
    'utf8',
  )
  const listSource = readFileSync(
    resolve(process.cwd(), 'src/views/tasks/TaskListView.vue'),
    'utf8',
  )

  it.each([
    'collaborator_ids',
    'reviewer',
    'delay_reason',
    'completion_note',
  ])('renders, synchronizes and submits %s without dropping it', (field) => {
    expect(dialogSource).toContain(`v-model="form.${field}"`)
    expect(dialogSource).toContain(`data.${field}`)
    expect(listSource).toContain(`task.${field}`)
  })

  it('prompts for a reason before a board transition enters overdue', () => {
    expect(listSource).toContain("if (newStatus === 'overdue')")
    expect(listSource).toContain('inputValidator')
    expect(listSource).toContain("if (newStatus === 'pending_review')")
    expect(listSource).toContain(
      'changeTaskStatus(task.id, newStatus, delayReason, completionNote)',
    )
  })

  it('uses project_id/task_id deep links and exports the active filters', () => {
    expect(listSource).toContain('route.query.project_id')
    expect(listSource).toContain('queryParams.project = routeProjectId')
    expect(listSource).toContain('route.query.task_id')
    expect(listSource).toContain('if (canManageTask(task))')
    expect(listSource).toContain('导出当前结果')
    expect(listSource).toContain("exportData(\n      'tasks',\n      'xlsx'")
    for (const field of ['search', 'status', 'priority', 'assignee', 'scope']) {
      expect(listSource).toContain(`${field}: queryParams.${field}`)
    }
  })
})
