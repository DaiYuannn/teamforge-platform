export type WorkloadValue = number | string
export type CompetitionWorkItemStatus =
  | 'todo'
  | 'doing'
  | 'pending_review'
  | 'done'
  | 'paused'
  | 'cancelled'
  | 'need_help'

export interface CompetitionSubTask {
  id?: number
  title: string
  assignee: number | null
  assignee_name?: string
  is_completed: boolean
  completed_at?: string | null
  sort_order: number
}

export interface CompetitionWorkItem {
  id: number
  competition: number
  event_name: string
  event_edition: string
  entry_name: string
  project: number
  project_name: string
  assignee: number
  assignee_name: string
  collaborators: number[]
  collaborator_names: string[]
  reviewer: number | null
  reviewer_name: string
  title: string
  description: string
  deadline: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: string
  status_display: string
  completed_at: string | null
  completion_note: string
  reference_note: string
  subtasks: CompetitionSubTask[]
  created_by_name: string
  can_manage: boolean
  can_edit: boolean
  can_review: boolean
  created_at: string
  updated_at: string
}

export interface CompetitionWorkItemInput {
  competition: number
  assignee?: number
  collaborators?: number[]
  reviewer?: number | null
  title: string
  description?: string
  deadline: string
  priority?: 'low' | 'medium' | 'high' | 'urgent'
  reference_note?: string
  completion_note?: string
  subtasks?: CompetitionSubTask[]
  status?: CompetitionWorkItemStatus
}

export interface WorkloadAllocation {
  id: number
  user: number
  user_name: string
  percentage: WorkloadValue
  rationale: string
}

export interface WorkloadAssessment {
  id: number
  competition: number
  project: number
  project_name: string
  event_name: string
  event_edition: string
  entry_name: string
  version: number
  status: string
  status_display: string
  decision_note: string
  decided_by_name: string
  published_at: string | null
  is_current: boolean
  allocations: WorkloadAllocation[]
  allocation_total: WorkloadValue
  objection_count: number
  can_manage: boolean
  can_object: boolean
}

export interface WorkloadAllocationInput {
  user: number
  percentage: number
  rationale: string
}

export interface WorkloadAssessmentDraftInput {
  competition: number
  decision_note: string
  allocations: WorkloadAllocationInput[]
}

export type WorkloadObjectionResolutionStatus = 'resolved' | 'rejected'

export interface WorkloadObjection {
  id: number
  allocation: number
  assessment: number
  competition: number
  allocation_user: number
  allocation_user_name: string
  raised_by: number
  raised_by_name: string
  reason: string
  status: string
  status_display: string
  response: string
  resolved_by_name: string
  created_at: string
  resolved_at: string | null
  can_resolve: boolean
}

export interface WorkloadObjectionInput {
  allocation: number
  reason: string
}

export interface WorkloadObjectionResolutionInput {
  status: WorkloadObjectionResolutionStatus
  response: string
}
