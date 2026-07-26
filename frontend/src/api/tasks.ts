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
export function changeTaskStatus(
  id: number,
  status: TaskStatus,
  delayReason?: string,
  completionNote?: string,
): Promise<Task> {
  return post<Task>(`/tasks/${id}/change_status/`, {
    to_status: status,
    delay_reason: delayReason,
    completion_note: completionNote,
  })
}

/** 按项目获取全部任务，避免项目详情只展示第一页。 */
export async function getTasksByProject(projectId: number): Promise<Task[]> {
  const tasks: Task[] = []
  let page = 1

  while (true) {
    const response = await get<PaginatedResponse<Task> | Task[]>('/tasks/', {
      project: projectId,
      page,
      page_size: 100,
    })
    if (Array.isArray(response)) return response

    tasks.push(...response.results)
    if (!response.next || response.results.length === 0) return tasks
    page += 1
  }
}
