import { get, post, patch, del } from './request'
import type {
  PaginatedResponse,
  PaginationParams,
  Task,
  TaskFormData,
  TaskQueryParams,
  TaskStatus,
  User,
} from '@/types'

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

export interface SubTask {
  id: number
  parent: number
  parent_title: string
  title: string
  assignee: number | null
  assignee_detail?: User | null
  assignee_name?: string
  is_completed: boolean
  completed_at: string | null
  sort_order: number
  created_at: string
}

export interface SubTaskInput {
  parent: number
  title: string
  assignee?: number | null
  sort_order?: number
}

export interface SubTaskQuery extends PaginationParams {
  parent?: number
  assignee?: number
  is_completed?: boolean
}

export function getSubTasks(params: SubTaskQuery): Promise<PaginatedResponse<SubTask>> {
  return get<PaginatedResponse<SubTask>>('/tasks/subtasks/', params)
}

export function createSubTask(data: SubTaskInput): Promise<SubTask> {
  return post<SubTask>('/tasks/subtasks/', data)
}

export function updateSubTask(id: number, data: Partial<SubTaskInput>): Promise<SubTask> {
  return patch<SubTask>(`/tasks/subtasks/${id}/`, data)
}

export function deleteSubTask(id: number): Promise<void> {
  return del<void>(`/tasks/subtasks/${id}/`)
}

export function toggleSubTask(id: number): Promise<SubTask> {
  return post<SubTask>(`/tasks/subtasks/${id}/toggle/`)
}

export interface TaskDependency {
  id: number
  task: number
  task_title: string
  depends_on: number
  depends_on_title: string
  created_at: string
}

export interface TaskDependencyQuery extends PaginationParams {
  task?: number
  depends_on?: number
}

export function getTaskDependencies(
  params: TaskDependencyQuery,
): Promise<PaginatedResponse<TaskDependency>> {
  return get<PaginatedResponse<TaskDependency>>('/tasks/dependencies/', params)
}

export function getTaskDependency(id: number): Promise<TaskDependency> {
  return get<TaskDependency>(`/tasks/dependencies/${id}/`)
}

export function createTaskDependency(data: {
  task: number
  depends_on: number
}): Promise<TaskDependency> {
  return post<TaskDependency>('/tasks/dependencies/', data)
}

export function deleteTaskDependency(id: number): Promise<void> {
  return del<void>(`/tasks/dependencies/${id}/`)
}

export interface TaskComment {
  id: number
  task: number
  task_title: string
  author: number
  author_detail?: User
  author_name: string
  content: string
  parent: number | null
  replies: TaskComment[]
  created_at: string
  updated_at: string
}

export interface TaskCommentQuery extends PaginationParams {
  task?: number
  author?: number
  parent?: number | null
}

export interface TaskCommentInput {
  task: number
  content: string
  parent?: number | null
}

export function getTaskComments(params: TaskCommentQuery): Promise<PaginatedResponse<TaskComment>> {
  return get<PaginatedResponse<TaskComment>>('/tasks/comments/', params)
}

export function getTaskComment(id: number): Promise<TaskComment> {
  return get<TaskComment>(`/tasks/comments/${id}/`)
}

export function createTaskComment(data: TaskCommentInput): Promise<TaskComment> {
  return post<TaskComment>('/tasks/comments/', data)
}

export function updateTaskComment(
  id: number,
  data: Partial<TaskCommentInput>,
): Promise<TaskComment> {
  return patch<TaskComment>(`/tasks/comments/${id}/`, data)
}

export function deleteTaskComment(id: number): Promise<void> {
  return del<void>(`/tasks/comments/${id}/`)
}
