import { get, post, patch, del } from './request'
import type { Task, TaskFormData, TaskQueryParams, TaskStatus, PaginatedResponse } from '@/types'

export type { TaskQueryParams }

/** 获取任务列表 */
export function getTasks(params: TaskQueryParams): Promise<PaginatedResponse<Task>> {
  return get<PaginatedResponse<Task>>('/tasks/', params)
}

/** 获取任务详情 */
export function getTask(id: number): Promise<Task> {
  return get<Task>(`/tasks/${id}/`)
}

/** 创建任务 */
export function createTask(data: TaskFormData): Promise<Task> {
  return post<Task>('/tasks/', data)
}

/** 更新任务 */
export function updateTask(id: number, data: Partial<TaskFormData>): Promise<Task> {
  return patch<Task>(`/tasks/${id}/`, data)
}

/** 删除任务 */
export function deleteTask(id: number): Promise<void> {
  return del<void>(`/tasks/${id}/`)
}

/** 修改任务状态（拖拽看板时调用） */
export function changeTaskStatus(id: number, status: TaskStatus, delayReason?: string): Promise<Task> {
  return post<Task>(`/tasks/${id}/change_status/`, { to_status: status, delay_reason: delayReason })
}

/** 按项目获取任务列表 */
export function getTasksByProject(projectId: number): Promise<Task[]> {
  return get<Task[]>('/tasks/', { project: projectId, page_size: 999 })
}
