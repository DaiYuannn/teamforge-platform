// ============================================
// 知识产权模块类型定义
// ============================================

// 知识产权成果类型
export type IPType = 'software_copyright' | 'invention_patent' | 'utility_model' | 'design_patent' | 'paper' | 'other'

// 申请状态（14种）
export type IPStatus = 'draft' | 'writing' | 'leader_review' | 'teacher_confirm' | 'research_office_review' | 'returned' | 'modifying' | 'resubmitted' | 'accepted' | 'authorized' | 'archived' | 'paused' | 'terminated' | 'deferred'

// 贡献者角色
export type ContributorRole = 'main_writer' | 'co_writer' | 'code_provider' | 'document_writer' | 'drawing_provider' | 'tester' | 'executor' | 'material_manager' | 'reviewer'

// 退回来源
export type ReturnSource = 'research_office' | 'school_system' | 'agency' | 'patent_platform' | 'other'

// 责任类型
export type ResponsibilityType = 'writing_problem' | 'material_problem' | 'submit_problem' | 'review_problem' | 'system_problem' | 'unattributable' | 'other'

// 退回结果
export type ReturnResult = 'pending' | 'modified' | 'resubmitted' | 'accepted' | 'rejected'

// 材料类型
export type MaterialType = 'application_form' | 'manual' | 'source_code' | 'screenshot' | 'disclosure' | 'specification' | 'claims' | 'abstract' | 'drawing' | 'feedback' | 'system_screenshot' | 'acceptance_notice' | 'certificate' | 'archive' | 'other'

// 异议类型
export type ObjectionType = 'writing_credit' | 'execution_credit' | 'return_responsibility' | 'ranking' | 'material_credit' | 'other'

// 异议状态
export type ObjectionStatus = 'pending' | 'leader_reviewed' | 'teacher_confirmed' | 'resolved' | 'rejected'

// 知识产权申请
export interface IPApplication {
  id: number
  title: string
  application_code: string
  ip_type: IPType
  related_project?: number | null
  related_project_name?: string
  status: IPStatus
  main_writer?: number | null
  main_writer_name?: string
  main_writer_detail?: any
  applicant_executor?: number | null
  applicant_executor_name?: string
  applicant_executor_detail?: any
  material_manager?: number | null
  material_manager_name?: string
  material_manager_detail?: any
  project_reviewer?: number | null
  project_reviewer_name?: string
  project_reviewer_detail?: any
  teacher_confirmer?: number | null
  teacher_confirmer_name?: string
  teacher_confirmer_detail?: any
  start_date?: string | null
  submit_date?: string | null
  accepted_date?: string | null
  authorized_date?: string | null
  return_count: number
  current_problem: string
  final_certificate_file?: number | null
  final_certificate_file_name?: string
  intro: string
  created_by?: number | null
  created_by_name?: string
  created_at: string
  updated_at: string
  // 详情才有的嵌套数据
  contributors?: IPContributor[]
  return_records?: IPReturnRecord[]
  material_versions?: IPMaterialVersion[]
  objections?: IPObjection[]
}

// 列表精简版
export interface IPApplicationListItem {
  id: number
  title: string
  application_code: string
  ip_type: IPType
  ip_type_display?: string
  related_project?: number | null
  related_project_name?: string
  status: IPStatus
  status_display?: string
  main_writer?: number | null
  main_writer_name?: string
  applicant_executor?: number | null
  applicant_executor_name?: string
  return_count: number
  created_at: string
  updated_at: string
}

// 责任分工
export interface IPContributor {
  id: number
  application: number
  user: number
  user_name?: string
  user_detail?: any
  role: ContributorRole
  contribution_description: string
  responsibility_description: string
  is_confirmed: boolean
  confirmed_by?: number | null
  confirmed_by_name?: string
  confirmed_at?: string | null
  created_at: string
}

// 退回记录
export interface IPReturnRecord {
  id: number
  application: number
  return_time: string
  return_source: ReturnSource
  return_reason: string
  responsibility_type: ResponsibilityType
  responsible_user?: number | null
  responsible_user_name?: string
  assigned_by?: number | null
  assigned_by_name?: string
  modify_deadline?: string | null
  actual_modifier?: number | null
  actual_modifier_name?: string
  modify_description: string
  result: ReturnResult
  proof_file?: number | null
  created_at: string
  updated_at: string
}

// 材料版本
export interface IPMaterialVersion {
  id: number
  application: number
  file_asset: number
  file_asset_name?: string
  material_type: MaterialType
  version: string
  uploaded_by?: number | null
  uploaded_by_name?: string
  change_note: string
  related_return_record?: number | null
  is_final: boolean
  created_at: string
}

// 异议
export interface IPObjection {
  id: number
  application: number
  objector: number
  objector_name?: string
  objector_detail?: any
  objection_type: ObjectionType
  content: string
  proof_file?: number | null
  status: ObjectionStatus
  leader_opinion: string
  leader_reviewer?: number | null
  leader_reviewer_name?: string
  leader_reviewed_at?: string | null
  teacher_opinion: string
  teacher_confirmer?: number | null
  teacher_confirmer_name?: string
  teacher_confirmed_at?: string | null
  final_result: string
  created_at: string
  updated_at: string
}

// 待办事项
export interface IPTodoItem {
  type: 'writing' | 'return_fix' | 'submit' | 'review' | 'confirm' | 'objection' | 'my_objection'
  application_id: number
  title: string
  description: string
  deadline?: string | null
  created_at: string
}

export interface IPPaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type IPTodoResponse = IPPaginatedResponse<IPApplicationListItem> | IPApplicationListItem[]

export interface IPParticipantOption {
  id: number
  name?: string
  username?: string
  email?: string
  global_role?: string
  membership_status?: 'active' | 'on_leave' | 'exited' | 'external'
  is_active?: boolean
}
