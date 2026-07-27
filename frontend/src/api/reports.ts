import { del, download, get, patch, post } from './request'
import type { PaginatedResponse } from '@/types'

export type ReportDataSource = 'project' | 'task' | 'finance' | 'competition'
export type ReportFrequency = 'daily' | 'weekly' | 'monthly'
export type ReportFileFormat = 'xlsx' | 'docx' | 'pdf'
export type ReportRunStatus = 'never' | 'running' | 'success' | 'partial' | 'failed'

export interface CustomReport {
  id: number
  name: string
  description: string
  report_type: string
  config: {
    data_source: ReportDataSource
    filters?: Record<string, unknown>
    group_by?: string
    chart_type?: string
  }
  created_by?: number
  created_by_name?: string
  created_at: string
  updated_at: string
}

export interface ReportExecution {
  id: number
  schedule: number
  trigger: 'manual' | 'scheduled'
  trigger_display: string
  status: ReportRunStatus
  status_display: string
  file_name: string
  file_format: string
  file_size: number
  delivery_status: string
  delivery_status_display: string
  message: string
  error: string
  started_at: string
  finished_at?: string
  download_url: string
}

export interface ScheduledReport {
  id: number
  report: number
  report_name: string
  created_by?: number
  created_by_name?: string
  can_manage?: boolean
  recipient_ids: number[]
  recipient_names: string[]
  frequency: ReportFrequency
  frequency_display: string
  execution_time: string
  weekday: number
  day_of_month: number
  timezone: string
  file_format: ReportFileFormat
  file_format_display: string
  last_run?: string
  next_run?: string
  last_status: ReportRunStatus
  last_status_display: string
  last_error: string
  is_active: boolean
  recent_executions: ReportExecution[]
  created_at: string
  updated_at: string
}

export interface CustomReportPayload {
  name: string
  description?: string
  report_type: string
  config: CustomReport['config']
}

export interface GeneratedReportData {
  report_type: 'summary' | 'comparison' | 'trend'
  data_source: ReportDataSource
  group_by: string
  chart_type: string
  filters: Record<string, unknown>
  summary: Record<string, string | number>
  value_key: 'count' | 'total'
  comparison?: { average: number; maximum: number; minimum: number }
  groups: Array<{
    key: string | number | null
    label: string
    count: number
    total?: number
    rank?: number
    share_percent?: number
    delta_from_average?: number
  }>
}

export interface GeneratedReport {
  report: CustomReport
  generated_at: string
  data: GeneratedReportData
}

export interface SchedulePayload {
  report: number
  recipient_ids: number[]
  frequency: ReportFrequency
  execution_time: string
  weekday: number
  day_of_month: number
  timezone: string
  file_format: ReportFileFormat
  is_active: boolean
}

export const getCustomReports = () =>
  get<PaginatedResponse<CustomReport>>('/exports/custom-reports/', { page: 1, page_size: 100 })

export const createCustomReport = (payload: CustomReportPayload) =>
  post<CustomReport>('/exports/custom-reports/', payload)

export const updateCustomReport = (id: number, payload: Partial<CustomReportPayload>) =>
  patch<CustomReport>(`/exports/custom-reports/${id}/`, payload)

export const deleteCustomReport = (id: number) =>
  del<void>(`/exports/custom-reports/${id}/`)

export const generateCustomReport = (id: number) =>
  post<GeneratedReport>(`/exports/custom-reports/${id}/generate/`)

export const getScheduledReports = () =>
  get<PaginatedResponse<ScheduledReport>>('/exports/scheduled-reports/', { page: 1, page_size: 100 })

export const createScheduledReport = (payload: SchedulePayload) =>
  post<ScheduledReport>('/exports/scheduled-reports/', payload)

export const updateScheduledReport = (id: number, payload: Partial<SchedulePayload>) =>
  patch<ScheduledReport>(`/exports/scheduled-reports/${id}/`, payload)

export const deleteScheduledReport = (id: number) =>
  del<void>(`/exports/scheduled-reports/${id}/`)

export const runScheduledReport = (id: number) =>
  post<ReportExecution>(`/exports/scheduled-reports/${id}/run_now/`)

export const activateScheduledReport = (id: number) =>
  post<ScheduledReport>(`/exports/scheduled-reports/${id}/activate/`)

export const deactivateScheduledReport = (id: number) =>
  post<ScheduledReport>(`/exports/scheduled-reports/${id}/deactivate/`)

export const downloadReportExecution = (scheduleId: number, executionId: number): Promise<Blob> =>
  download(`/exports/scheduled-reports/${scheduleId}/executions/${executionId}/download/`)
