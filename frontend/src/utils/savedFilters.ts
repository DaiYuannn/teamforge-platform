import {
  PROJECT_STATUS_MAP,
  TASK_PRIORITY_MAP,
  TASK_STATUS_MAP,
} from '@/utils/constants'
import type { TaskPriority, TaskStatus } from '@/types'

export type AccountScope = 'mine' | 'team'

export interface ProjectSavedFilters {
  search?: string
  status?: string
  leader?: string
  start_date?: string
  end_date?: string
  ordering?: string
  scope?: AccountScope
}

export interface TaskSavedFilters {
  search?: string
  project?: number
  status?: TaskStatus
  priority?: TaskPriority
  assignee?: number
  scope?: AccountScope
}

const PROJECT_ORDERINGS = new Set([
  '-created_at',
  'created_at',
  '-start_date',
  'start_date',
])
const PROJECT_STATUSES = new Set(Object.keys(PROJECT_STATUS_MAP))
const TASK_STATUSES = new Set<TaskStatus>(Object.keys(TASK_STATUS_MAP) as TaskStatus[])
const TASK_PRIORITIES = new Set<TaskPriority>(Object.keys(TASK_PRIORITY_MAP) as TaskPriority[])

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function normalizedText(value: unknown, maxLength: number): string | undefined {
  if (typeof value !== 'string') return undefined
  const normalized = value.trim()
  if (!normalized || normalized.length > maxLength) return undefined
  return normalized
}

function normalizedChoice<T extends string>(
  value: unknown,
  choices: ReadonlySet<T>,
): T | undefined {
  return (
    typeof value === 'string'
    && choices.has(value as T)
  ) ? value as T : undefined
}

function normalizedScope(value: unknown): AccountScope | undefined {
  return value === 'mine' || value === 'team' ? value : undefined
}

function normalizedPositiveInteger(value: unknown): number | undefined {
  if (typeof value === 'string' && /^\d+$/.test(value)) {
    value = Number(value)
  }
  return (
    typeof value === 'number'
    && Number.isSafeInteger(value)
    && value > 0
  ) ? value : undefined
}

function normalizedDate(value: unknown): string | undefined {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return undefined
  }
  const parsed = new Date(`${value}T00:00:00Z`)
  return (
    Number.isFinite(parsed.getTime())
    && parsed.toISOString().slice(0, 10) === value
  ) ? value : undefined
}

function assignIfDefined<T extends object, K extends keyof T>(
  target: T,
  key: K,
  value: T[K] | undefined,
): void {
  if (value !== undefined) target[key] = value
}

/** 只恢复项目页明确支持的字段；未知键、错误类型和非法枚举全部丢弃。 */
export function normalizeProjectSavedFilters(value: unknown): ProjectSavedFilters {
  if (!isRecord(value)) return {}
  const normalized: ProjectSavedFilters = {}
  assignIfDefined(normalized, 'search', normalizedText(value.search, 200))
  assignIfDefined(normalized, 'status', normalizedChoice(value.status, PROJECT_STATUSES))
  const leader = (
    normalizedPositiveInteger(value.leader)?.toString()
    ?? normalizedText(value.leader, 100)
  )
  assignIfDefined(normalized, 'leader', leader)
  assignIfDefined(normalized, 'start_date', normalizedDate(value.start_date))
  assignIfDefined(normalized, 'end_date', normalizedDate(value.end_date))
  assignIfDefined(normalized, 'ordering', normalizedChoice(value.ordering, PROJECT_ORDERINGS))
  assignIfDefined(normalized, 'scope', normalizedScope(value.scope))
  return normalized
}

/** 只恢复任务页明确支持的字段，并把合法数字字符串规范为数字 ID。 */
export function normalizeTaskSavedFilters(value: unknown): TaskSavedFilters {
  if (!isRecord(value)) return {}
  const normalized: TaskSavedFilters = {}
  assignIfDefined(normalized, 'search', normalizedText(value.search, 200))
  assignIfDefined(normalized, 'project', normalizedPositiveInteger(value.project))
  assignIfDefined(normalized, 'status', normalizedChoice(value.status, TASK_STATUSES))
  assignIfDefined(normalized, 'priority', normalizedChoice(value.priority, TASK_PRIORITIES))
  assignIfDefined(normalized, 'assignee', normalizedPositiveInteger(value.assignee))
  assignIfDefined(normalized, 'scope', normalizedScope(value.scope))
  return normalized
}

/**
 * 合并保存单个页面的筛选，不修改输入对象，也不覆盖其他页面的偏好。
 * filters 为 null 时仅移除指定页面。
 */
export function mergeSavedFilterModule(
  current: unknown,
  module: 'projects' | 'tasks',
  filters: object | null,
): Record<string, Record<string, unknown>> {
  const merged: Record<string, Record<string, unknown>> = {}
  if (isRecord(current)) {
    for (const [key, value] of Object.entries(current)) {
      if (isRecord(value)) merged[key] = { ...value }
    }
  }
  if (filters === null) {
    delete merged[module]
  } else {
    merged[module] = { ...filters }
  }
  return merged
}

export function hasSavedFilterModule(
  current: unknown,
  module: 'projects' | 'tasks',
): boolean {
  return isRecord(current) && Object.prototype.hasOwnProperty.call(current, module)
}
