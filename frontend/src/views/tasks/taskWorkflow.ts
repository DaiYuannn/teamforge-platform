import type { Task, TaskStatus } from '@/types'

export function parsePositiveRouteId(value: unknown): number | undefined {
  const candidate = Array.isArray(value) ? value[0] : value
  if (typeof candidate !== 'string' && typeof candidate !== 'number') {
    return undefined
  }
  const parsed = Number(candidate)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

const MANAGER_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  todo: ['doing', 'overdue', 'paused', 'cancelled', 'need_help'],
  doing: ['pending_review', 'overdue', 'paused', 'cancelled', 'need_help'],
  pending_review: ['done', 'doing', 'overdue', 'paused', 'cancelled'],
  overdue: ['doing', 'pending_review', 'paused', 'cancelled', 'need_help'],
  paused: ['todo', 'doing', 'overdue', 'cancelled'],
  cancelled: ['todo'],
  need_help: ['doing', 'pending_review', 'overdue', 'paused', 'cancelled'],
  done: ['doing'],
}

const PARTICIPANT_TRANSITIONS: Partial<Record<TaskStatus, TaskStatus[]>> = {
  todo: ['doing', 'need_help'],
  doing: ['pending_review', 'need_help'],
  overdue: ['doing', 'pending_review', 'need_help'],
  need_help: ['doing', 'pending_review'],
}

const REVIEWER_TRANSITIONS: Partial<Record<TaskStatus, TaskStatus[]>> = {
  pending_review: ['done', 'doing'],
}

export function getManagerTaskStatusTargets(status: TaskStatus): TaskStatus[] {
  return [...MANAGER_TRANSITIONS[status]]
}

export function getAllowedTaskStatusTargets(
  task: Task,
  userId: number | undefined,
  isManager: boolean,
): TaskStatus[] {
  if (!userId) return []
  if (isManager) return getManagerTaskStatusTargets(task.status)

  const targets = new Set<TaskStatus>()
  const isParticipant = (
    task.assignee === userId
    || Boolean(task.collaborator_ids?.includes(userId))
  )
  if (isParticipant) {
    for (const status of PARTICIPANT_TRANSITIONS[task.status] || []) {
      targets.add(status)
    }
  }
  if (task.reviewer === userId) {
    for (const status of REVIEWER_TRANSITIONS[task.status] || []) {
      targets.add(status)
    }
  }
  return Array.from(targets)
}

export function canTransitionTaskStatus(
  task: Task,
  target: TaskStatus,
  userId: number | undefined,
  isManager: boolean,
): boolean {
  return getAllowedTaskStatusTargets(task, userId, isManager).includes(target)
}
