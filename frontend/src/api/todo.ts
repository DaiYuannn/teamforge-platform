import { get } from './request'

export interface UnifiedTodoItem {
  id: number | string
  type: 'task' | 'overdue_task' | 'approval' | 'contribution_review' | 'ip_todo' | string
  title: string
  url: string
  route_name?: string
  route_params?: Record<string, number | string>
  route_query?: Record<string, number | string>
  priority?: string
  due_date?: string | null
  project_id?: number | null
  project_name?: string
  status?: string
  status_display?: string
}

export interface UnifiedTodoResponse {
  count: number
  results: UnifiedTodoItem[]
}

export function getUnifiedTodos(type?: string): Promise<UnifiedTodoResponse> {
  return get('/todo/', type ? { type } : undefined)
}
