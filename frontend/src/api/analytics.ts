import { del, get, patch, post } from './request'
import type { PaginatedResponse } from '@/types'

export type DashboardWidget = 'signals' | 'priority' | 'delivery' | 'business'

export interface CustomDashboardConfig {
  widgets: DashboardWidget[]
  columns: 1 | 2 | 3 | 4
  date_range: 'week' | 'month' | 'quarter'
  project_id?: number | null
}

export interface CustomDashboard {
  id: number
  user: number
  user_name: string
  name: string
  config: CustomDashboardConfig
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface CustomDashboardPayload {
  name: string
  config: CustomDashboardConfig
  is_default: boolean
}

export interface DashboardMetric {
  label: string
  value: number | string
  format?: 'currency'
  route?: string
}

export interface CustomDashboardRuntimeData {
  dashboard: CustomDashboard
  generated_at: string
  widgets: Record<string, {
    total?: number
    metrics?: DashboardMetric[]
    items?: Array<Record<string, unknown> & { route?: string }>
  }>
}

export interface WeeklyReportSummary {
  report_period_start: string
  report_period_end: string
  weeks: number
  tasks_completed: number
  tasks_new: number
  tasks_pending: number
  tasks_overdue: number
  tasks_upcoming_deadline: number
  active_projects: number
  stage_changes: number
  weekly_expense: number
  team_activities: number
}

export interface WeeklyTask {
  task_id: number
  title: string
  status: string
  status_display: string
  project_id?: number | null
  project_name?: string
  assignee_id?: number | null
  assignee_name?: string
  deadline?: string | null
  completed_at?: string | null
}

export interface WeeklyProjectProgress {
  project_id: number
  project_name: string
  project_code: string
  current_stage: number
  current_stage_display: string
  tasks_completed_this_week: number
  tasks_new_this_week: number
  last_update?: string | null
}

export interface WeeklyReport {
  summary: WeeklyReportSummary
  narrative: string
  completed_tasks: WeeklyTask[]
  new_tasks: WeeklyTask[]
  pending_tasks: WeeklyTask[]
  overdue_tasks: WeeklyTask[]
  upcoming_deadline_tasks: WeeklyTask[]
  project_progress: WeeklyProjectProgress[]
  stage_changes: Array<Record<string, unknown>>
  upcoming_competitions: Array<Record<string, unknown>>
  team_activity: Array<Record<string, unknown>>
}

export const getCustomDashboards = () =>
  get<PaginatedResponse<CustomDashboard>>('/dashboard/custom/', { page: 1, page_size: 100 })
export const createCustomDashboard = (payload: CustomDashboardPayload) =>
  post<CustomDashboard>('/dashboard/custom/', payload)
export const updateCustomDashboard = (id: number, payload: Partial<CustomDashboardPayload>) =>
  patch<CustomDashboard>(`/dashboard/custom/${id}/`, payload)
export const deleteCustomDashboard = (id: number) =>
  del<void>(`/dashboard/custom/${id}/`)
export const setDefaultDashboard = (id: number) =>
  post<CustomDashboard>(`/dashboard/custom/${id}/set_default/`)
export const getCustomDashboardData = (id: number) =>
  get<CustomDashboardRuntimeData>(`/dashboard/custom/${id}/data/`)

export const getWeeklyReport = (params?: { project_id?: number; weeks?: number }) =>
  get<WeeklyReport>('/dashboard/weekly-report/', params)
