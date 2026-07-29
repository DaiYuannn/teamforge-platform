import { del, get, patch, post } from './request'
import type { PaginatedResponse } from '@/types'

export interface ListQuery {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: string | number | boolean | undefined
}

export interface CustomRole {
  id: number
  name: string
  description: string
  permissions: string[]
  is_system: boolean
  created_at: string
}

export interface CustomRolePayload {
  name: string
  description?: string
  permissions: string[]
}

export interface RoleAssignment {
  id: number
  user: number
  user_name: string
  role: number
  role_name: string
  project?: number | null
  project_name?: string
  assigned_by?: number | null
  assigned_by_name?: string
  created_at: string
}

export interface RoleAssignmentPayload {
  user: number
  role: number
  project?: number | null
}

export interface ApprovalStep {
  name: string
  reviewer_role?: string
  reviewer_roles?: string[]
  reviewer_ids?: number[]
}

export interface ApprovalFlow {
  id: number
  name: string
  flow_type: string
  steps: ApprovalStep[]
  is_active: boolean
  created_at: string
}

export interface ApprovalFlowPayload {
  name: string
  flow_type: string
  steps: ApprovalStep[]
  is_active: boolean
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface ApprovalRequest {
  id: number
  applicant: number
  applicant_name: string
  flow: number
  flow_name: string
  flow_type: string
  status: ApprovalStatus
  status_display: string
  title: string
  content: string
  current_step: number
  current_step_name: string
  reviewer_ids: number[]
  reviewer_roles: string[]
  reviewer_names: string[]
  can_review: boolean
  review_history: ApprovalReviewHistory[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ApprovalReviewHistory {
  action: 'approve' | 'reject' | 'cancel' | string
  opinion: string
  by: number
  by_name?: string
  step: number
  step_name: string
  at?: string
}

export type TeamMembershipAction = 'join' | 'transfer' | 'role_change'

export interface TeamMembershipApprovalMetadata {
  [key: string]: string | number | undefined
  action: TeamMembershipAction
  target_team_id: number
  membership_id?: number
  requested_role: string
  reason: string
}

export interface ApprovalRequestPayload {
  flow: number
  title: string
  content?: string
  metadata?: Record<string, unknown>
}

export type CustomFormFieldType = 'text' | 'textarea' | 'number' | 'date' | 'select' | 'switch'

export interface CustomFormField {
  key: string
  label: string
  type: CustomFormFieldType
  required?: boolean
  placeholder?: string
  options?: string[]
}

export interface CustomForm {
  id: number
  name: string
  description: string
  fields: CustomFormField[]
  created_by?: number | null
  created_by_name?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CustomFormPayload {
  name: string
  description?: string
  fields: CustomFormField[]
  is_active: boolean
}

export interface FormSubmission {
  id: number
  form: number
  form_name: string
  user?: number | null
  user_name?: string
  data: Record<string, unknown>
  created_at: string
}

export interface ExternalPlatform {
  id: number
  name: string
  platform_type: string
  api_url: string
  is_active: boolean
  config: Record<string, unknown>
  connection_status: 'unchecked' | 'connected' | 'error'
  last_checked_at?: string | null
  last_synced_at?: string | null
  last_error?: string
  remote_metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ExternalPlatformPayload {
  name: string
  platform_type: string
  api_url?: string
  api_key?: string
  is_active: boolean
  config?: Record<string, unknown>
}

export interface GitRepository {
  id: number
  url: string
  branch: string
  project: number
  project_name: string
  created_by?: number | null
  created_by_name?: string
  is_active: boolean
  connection_status: 'unchecked' | 'connected' | 'error'
  last_checked_at?: string | null
  last_synced_at?: string | null
  last_error?: string
  remote_commit?: string
  created_at: string
  updated_at: string
}

export interface GitRepositoryPayload {
  url: string
  branch: string
  token?: string
  project: number
  is_active: boolean
}

const listParams = (params?: ListQuery) => ({ page: 1, page_size: 100, ...params })

export const getCustomRoles = (params?: ListQuery) =>
  get<PaginatedResponse<CustomRole>>('/users/roles/', listParams(params))
export const createCustomRole = (payload: CustomRolePayload) =>
  post<CustomRole>('/users/roles/', payload)
export const updateCustomRole = (id: number, payload: Partial<CustomRolePayload>) =>
  patch<CustomRole>(`/users/roles/${id}/`, payload)
export const deleteCustomRole = (id: number) => del<void>(`/users/roles/${id}/`)

export const getRoleAssignments = (params?: ListQuery) =>
  get<PaginatedResponse<RoleAssignment>>('/users/role-assignments/', listParams(params))
export const createRoleAssignment = (payload: RoleAssignmentPayload) =>
  post<RoleAssignment>('/users/role-assignments/', payload)
export const updateRoleAssignment = (id: number, payload: Partial<RoleAssignmentPayload>) =>
  patch<RoleAssignment>(`/users/role-assignments/${id}/`, payload)
export const deleteRoleAssignment = (id: number) =>
  del<void>(`/users/role-assignments/${id}/`)

export const getApprovalFlows = (params?: ListQuery) =>
  get<PaginatedResponse<ApprovalFlow>>('/approvals/flows/', listParams(params))
export const createApprovalFlow = (payload: ApprovalFlowPayload) =>
  post<ApprovalFlow>('/approvals/flows/', payload)
export const updateApprovalFlow = (id: number, payload: Partial<ApprovalFlowPayload>) =>
  patch<ApprovalFlow>(`/approvals/flows/${id}/`, payload)
export const deleteApprovalFlow = (id: number) => del<void>(`/approvals/flows/${id}/`)

export const getApprovalRequests = (params?: ListQuery) =>
  get<PaginatedResponse<ApprovalRequest>>('/approvals/requests/', listParams(params))
export const createApprovalRequest = (payload: ApprovalRequestPayload) =>
  post<ApprovalRequest>('/approvals/requests/', payload)
export const approveApprovalRequest = (id: number, opinion = '') =>
  post<ApprovalRequest>(`/approvals/requests/${id}/approve/`, { opinion })
export const rejectApprovalRequest = (id: number, opinion = '') =>
  post<ApprovalRequest>(`/approvals/requests/${id}/reject/`, { opinion })
export const cancelApprovalRequest = (id: number) =>
  post<ApprovalRequest>(`/approvals/requests/${id}/cancel/`)

export const getCustomForms = (params?: ListQuery) =>
  get<PaginatedResponse<CustomForm>>('/common/forms/', listParams(params))
export const createCustomForm = (payload: CustomFormPayload) =>
  post<CustomForm>('/common/forms/', payload)
export const updateCustomForm = (id: number, payload: Partial<CustomFormPayload>) =>
  patch<CustomForm>(`/common/forms/${id}/`, payload)
export const deleteCustomForm = (id: number) => del<void>(`/common/forms/${id}/`)

export const getFormSubmissions = (params?: ListQuery) =>
  get<PaginatedResponse<FormSubmission>>('/common/form-submissions/', listParams(params))
export const createFormSubmission = (form: number, data: Record<string, unknown>) =>
  post<FormSubmission>('/common/form-submissions/', { form, data })
export const deleteFormSubmission = (id: number) =>
  del<void>(`/common/form-submissions/${id}/`)

export const getExternalPlatforms = (params?: ListQuery) =>
  get<PaginatedResponse<ExternalPlatform>>('/integrations/external-platforms/', listParams(params))
export const createExternalPlatform = (payload: ExternalPlatformPayload) =>
  post<ExternalPlatform>('/integrations/external-platforms/', payload)
export const updateExternalPlatform = (id: number, payload: Partial<ExternalPlatformPayload>) =>
  patch<ExternalPlatform>(`/integrations/external-platforms/${id}/`, payload)
export const deleteExternalPlatform = (id: number) =>
  del<void>(`/integrations/external-platforms/${id}/`)
export const testExternalPlatform = (id: number) =>
  post<ExternalPlatform>(`/integrations/external-platforms/${id}/test-connection/`)
export const syncExternalPlatform = (id: number) =>
  post<ExternalPlatform>(`/integrations/external-platforms/${id}/sync/`)

export const getGitRepositories = (params?: ListQuery) =>
  get<PaginatedResponse<GitRepository>>('/integrations/git-repositories/', listParams(params))
export const createGitRepository = (payload: GitRepositoryPayload) =>
  post<GitRepository>('/integrations/git-repositories/', payload)
export const updateGitRepository = (id: number, payload: Partial<GitRepositoryPayload>) =>
  patch<GitRepository>(`/integrations/git-repositories/${id}/`, payload)
export const deleteGitRepository = (id: number) =>
  del<void>(`/integrations/git-repositories/${id}/`)
export const testGitRepository = (id: number) =>
  post<GitRepository>(`/integrations/git-repositories/${id}/test-connection/`)
export const syncGitRepository = (id: number) =>
  post<GitRepository>(`/integrations/git-repositories/${id}/sync/`)
