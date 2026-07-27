// ============================================
// 全局 TypeScript 类型定义
// ============================================

// 统一响应格式
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

// 分页响应格式
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// 分页查询参数
export interface PaginationParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
}

// ============================================
// 用户与认证
// ============================================

// 用户角色
export type UserRole = 'sys_admin' | 'teacher' | 'member' | 'sens_approver'
export type ThemeMode = 'light' | 'dark' | 'system' | 'schedule'

export interface UserPreferences {
  primary_color: string
  theme_color?: string
  theme_mode: ThemeMode
  schedule_start: string
  schedule_end: string
  default_landing: 'dashboard' | 'projects' | 'tasks' | 'notifications'
  sidebar_collapsed: boolean
  notification_sound: boolean
  language?: 'zh-CN' | 'en'
  items_per_page: 10 | 20 | 50
  default_scope?: 'mine' | 'team'
  sidebar_order?: string[]
  favorite_routes?: string[]
  saved_filters?: Record<string, Record<string, unknown>>
  notification_preferences?: {
    categories?: Record<string, boolean>
    channels?: Record<string, boolean>
    quiet_hours?: { enabled?: boolean; start?: string; end?: string }
    digest?: 'instant' | 'daily' | 'weekly'
  }
  dashboard_layout: {
    cards?: string[]
    [key: string]: unknown
  }
}

// 用户
export interface User {
  id: number
  username: string
  email: string
  name: string
  global_role: UserRole
  global_role_display?: string
  membership_status?: 'active' | 'on_leave' | 'exited' | 'external'
  team_joined_at?: string | null
  team_left_at?: string | null
  exit_reason?: string
  handover_to?: number | null
  handover_notes?: string
  avatar?: string
  phone?: string
  is_active: boolean
  date_joined: string
  last_login?: string
  preferences?: UserPreferences
}

// 登录请求参数
export interface LoginParams {
  email: string
  password: string
  remember_me?: boolean
}

// 登录响应数据
export interface LoginResult {
  token: {
    access: string
    refresh: string
  }
  user: User
}

// Token 刷新响应
export interface RefreshTokenResult {
  access: string
}

// 用户更新参数
export interface UpdateProfileParams {
  name?: string
  phone?: string
  avatar?: string
  email?: string
}

// 用户创建/更新参数
export interface UserFormData {
  username: string
  email: string
  name: string
  global_role: UserRole
  phone?: string
  password?: string
  password_confirm?: string
  is_active?: boolean
  membership_status?: 'active' | 'on_leave' | 'exited' | 'external'
  team_joined_at?: string | null
  handover_to?: number | null
  exit_reason?: string
  handover_notes?: string
}

// ============================================
// 项目
// ============================================

// 项目阶段（16阶段）
export type ProjectStage =
  | 'stage_01' | 'stage_02' | 'stage_03' | 'stage_04'
  | 'stage_05' | 'stage_06' | 'stage_07' | 'stage_08'
  | 'stage_09' | 'stage_10' | 'stage_11' | 'stage_12'
  | 'stage_13' | 'stage_14' | 'stage_15' | 'stage_16'
  | number

// 项目状态
export type ProjectStatus = 'active' | 'paused' | 'closed'

// 项目
export interface Project {
  id: number
  name: string
  code: string
  intro: string
  leader: number
  leader_name?: string
  current_stage?: number
  current_stage_display?: string
  status: ProjectStatus
  status_display?: string
  priority?: string
  priority_display?: string
  start_date: string
  planned_end_date: string
  actual_end_date?: string | null
  last_leader_update?: string | null
  created_at: string
  updated_at: string
  member_count?: number
  task_count?: number
  competition_count?: number
  finance_balance?: number | string
}

// 项目创建/更新参数
export interface ProjectFormData {
  name: string
  code: string
  intro?: string
  leader: number
  start_date: string
  planned_end_date: string
  status?: ProjectStatus
}

// 阶段流转参数
export interface AdvanceStageParams {
  target_stage: ProjectStage
  remark?: string
}

// 项目成员
export interface ProjectMember {
  id: number
  project: number
  user: number
  user_name: string
  user_avatar?: string
  user_detail?: any
  role_in_project: string
  role_in_project_display?: string
  status?: 'active' | 'on_leave' | 'exited'
  status_display?: string
  exited_at?: string | null
  exit_reason?: string
  handover_to?: number | null
  handover_to_name?: string
  handover_notes?: string
  joined_at: string
}

// 添加项目成员参数
export interface AddMemberParams {
  user: number
  role_in_project: string
}

export interface ProjectMembershipEvent {
  id: number
  event_type: string
  event_type_display: string
  from_role: string
  to_role: string
  from_status: string
  to_status: string
  reason: string
  handover_to?: number | null
  handover_to_name?: string
  operator_name?: string
  created_at: string
}

// 阶段流转日志
export interface StageLog {
  id: number
  project: number
  from_stage: ProjectStage | null
  to_stage: ProjectStage
  operator: number | null
  operator_name: string
  note?: string
  /** 兼容早期前端模拟数据字段，真实接口使用 note。 */
  remark?: string
  created_at: string
}

// ============================================
// 比赛
// ============================================

// 比赛级别
export type CompetitionLevel = 'school' | 'city' | 'province' | 'national'

// 比赛状态
export type CompetitionStatus = 'preparing' | 'ongoing' | 'completed'

// 比赛
export interface Competition {
  id: number
  project: number
  project_name?: string
  name: string
  level: CompetitionLevel
  level_display?: string
  status: CompetitionStatus
  status_display?: string
  description?: string
  comp_type?: string
  organizer: string
  register_date?: string | null
  material_deadline?: string | null
  review_date?: string | null
  defense_date?: string | null
  school_date?: string | null
  city_date?: string | null
  province_date?: string | null
  national_date?: string | null
  result_date?: string | null
  is_promoted: boolean
  is_awarded: boolean
  award_level: string
  not_promoted_reason: string
  improvement_suggestion: string
  review_summary: string
  current_stage: string
  created_at: string
  updated_at?: string
}

// 比赛创建/更新参数
export interface CompetitionFormData {
  project: number
  name: string
  comp_type: string
  level: CompetitionLevel
  status: CompetitionStatus
  organizer: string
  register_date: string | null
  material_deadline: string | null
  review_date: string | null
  defense_date: string | null
  school_date: string | null
  city_date: string | null
  province_date: string | null
  national_date: string | null
  result_date: string | null
  is_promoted: boolean
  is_awarded: boolean
  award_level: string
  not_promoted_reason: string
  improvement_suggestion: string
  review_summary: string
  current_stage: string
}

// ============================================
// 任务
// ============================================

// 任务状态
export type TaskStatus = 'todo' | 'doing' | 'pending_review' | 'done' | 'overdue' | 'paused' | 'cancelled' | 'need_help'

// 任务优先级
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

// 任务
export interface Task {
  id: number
  title: string
  description: string
  project: number
  project_name?: string
  assignee: number
  assignee_name: string
  assignee_avatar?: string
  creator?: number
  creator_name?: string
  reviewer?: number | null
  reviewer_name?: string
  collaborator_ids?: number[]
  collaborators_detail?: User[]
  status: TaskStatus
  priority?: TaskPriority
  priority_display?: string
  start_date?: string
  deadline: string
  delay_reason?: string
  completion_note?: string
  completed_at?: string | null
  created_at: string
  updated_at: string
  attachment_count?: number
  attachment_files?: FileAsset[]
}

// 任务创建/更新参数
export interface TaskFormData {
  title: string
  description?: string
  project: number
  assignee: number
  collaborator_ids?: number[]
  reviewer?: number | null
  status?: TaskStatus
  priority?: TaskPriority
  start_date?: string
  deadline: string
  delay_reason?: string
  completion_note?: string
  attachment_ids?: number[]
}

// 任务查询参数
export interface TaskQueryParams extends PaginationParams {
  project?: number
  status?: TaskStatus
  priority?: TaskPriority
  assignee?: number
  scope?: 'mine' | 'team'
}

// ============================================
// 经费
// ============================================

// 经费类别
export type FinanceCategory = 'material' | 'equipment' | 'printing' | 'travel' | 'software' | 'competition_fee' | 'promotion' | 'labor' | 'other'
export type ReimbursementStatus = 'draft' | 'pending' | 'approved' | 'rejected' | 'paid' | 'not_required'
export type FinanceIncomeType = 'bonus' | 'grant' | 'sponsorship' | 'refund' | 'other'

// 经费预算
export interface FinanceBudget {
  id: number
  project: number
  project_name?: string
  category: FinanceCategory
  amount: number
  bonus_amount: number
  other_income: number
  used_amount?: number
  pending_reimbursement?: number
  remaining_amount?: number
  total_income?: number
  period?: string
  status?: string
  description?: string
  created_at: string
  updated_at: string
}

// 经费支出
export interface FinanceExpense {
  id: number
  project: number
  project_name?: string
  category: FinanceCategory
  amount: number
  title: string
  spender?: number
  spender_name?: string
  reviewer?: number | null
  reviewer_name?: string
  expense_date: string
  purpose?: string
  receipts?: FinanceReceipt[]
  reimbursement_status?: ReimbursementStatus
  reimbursement_status_display?: string
  applied_by?: number | null
  applied_by_name?: string
  applied_at?: string | null
  reviewed_at?: string | null
  review_opinion?: string
  paid_by?: number | null
  paid_by_name?: string
  paid_at?: string | null
  payment_method?: string
  payment_reference?: string
  created_at: string
  updated_at: string
}

// 经费支出创建/更新参数
export interface FinanceExpenseFormData {
  project: number
  category: FinanceCategory
  amount: number
  title: string
  expense_date: string
  purpose?: string
  spender?: number | null
  reviewer?: number | null
}

// 经费票据
export interface FinanceReceipt {
  id: number
  expense: number
  file: string
  uploaded_by?: number
  uploaded_by_name?: string
  created_at?: string
}

export interface FinanceIncome {
  id: number
  project: number
  project_name?: string
  title: string
  amount: number | string
  income_type: FinanceIncomeType
  income_type_display?: string
  income_date: string
  source?: string
  reference_number?: string
  note?: string
  recorded_by?: number | null
  recorded_by_name?: string
  created_at: string
  updated_at: string
}

export interface FinanceIncomeFormData {
  project: number
  title: string
  amount: number
  income_type: FinanceIncomeType
  income_date: string
  source?: string
  reference_number?: string
  note?: string
}

// ============================================
// 文件管理
// ============================================

// 文件级别
export type FileLevel = 'public' | 'internal' | 'sensitive'

// 文件资源
export interface FileAsset {
  id: number
  project: number
  project_name?: string
  name: string
  file?: string
  file_url?: string
  content_type?: string
  size?: number
  level: FileLevel
  level_display?: string
  uploader?: number
  uploader_name: string
  version?: number
  description?: string
  created_at: string
  updated_at?: string
}

export interface FileVersion {
  id: number
  file_asset: number
  file?: string
  version: number
  uploader?: number
  uploader_name?: string
  created_at: string
}

// 文件上传参数
export interface FileUploadParams {
  project: number
  level: FileLevel
  description?: string
}

// 文件查询参数
export interface FileQueryParams extends PaginationParams {
  project?: number
  level?: FileLevel
}

// ============================================
// 导入中心
// ============================================

// 导入模块
export type ImportModule =
  | 'projects'
  | 'history_projects'
  | 'members'
  | 'tasks'
  | 'competitions'
  | 'finance'
  | 'ip_applications'

// 导入任务状态
export type ImportTaskStatus =
  | 'pending'
  | 'previewing'
  | 'previewed'
  | 'confirming'
  | 'confirmed'
  | 'failed'
  | 'rolled_back'

// 导入任务
export interface ImportTask {
  id: number
  module: ImportModule
  file_name: string
  status: ImportTaskStatus
  total_rows: number
  valid_rows: number
  error_rows: number
  error_details?: Record<string, string[] | string>
  field_mapping?: Record<string, string>
  created_by_name: string
  created_at: string
  updated_at?: string
  can_rollback: boolean
}

// 字段映射
export interface FieldMapping {
  [sourceField: string]: string
}

// 预览数据行
export interface PreviewRow {
  row_index: number
  data: Record<string, string>
  valid: boolean
  error?: string
}

// 导入预览结果
export interface ImportPreviewResult {
  task_id: number
  headers: string[]
  field_mapping: FieldMapping
  preview_rows: Record<string, any>[]
  total_rows: number
  valid_rows: number
  error_rows: number
  error_details: Record<string, any>
  field_options: Array<{ value: string; label: string; required: boolean }>
}

// ============================================
// 人员
// ============================================

// 成员信息
export interface Member {
  id: number
  username?: string
  user?: number
  user_name?: string
  name?: string
  email: string
  phone?: string
  avatar?: string
  global_role?: string
  global_role_display?: string
  membership_status?: 'active' | 'on_leave' | 'exited' | 'external'
  team_joined_at?: string | null
  team_left_at?: string | null
  exit_reason?: string
  handover_to?: number | null
  handover_notes?: string
  is_active?: boolean
  is_student?: boolean
  grade?: string
  major?: string
  student_id?: string
  department?: string
  position?: string
  project_count?: number
  task_count?: number
  projects?: { project_id: number; project_name: string; project_code: string; role_in_project: string; role_in_project_display: string; membership_status?: string; membership_status_display?: string; exited_at?: string | null; exit_reason?: string; project_status: string }[]
  tasks?: any[]
  skills?: any[]
  latest_work_schedule?: any
  date_joined?: string
  joined_projects?: { id: number; name: string; role_in_project: string }[]
}

// 成员更新参数
export interface MemberUpdateParams {
  grade?: string
  major?: string
  student_id?: string
  department?: string
  position?: string
  phone?: string
}

// ============================================
// 驾驶舱
// ============================================

// 驾驶舱统计数据
export interface DashboardData {
  project_overview?: { total: number; active: number; paused: number; closed: number; awarded?: number; stage_distribution?: Record<string, { name: string; count: number }> }
  finance_overview?: {
    total_bonus: string
    total_other_income: string
    total_income: string
    total_used: string
    total_pending: string
    total_remaining: string
    project_finance: any[]
  }
  task_overview?: {
    total: number
    overdue: number
    upcoming_deadline: number
    status_distribution: Record<string, { name: string; count: number }>
  }
  member_overview?: { total: number; teacher: number; member: number; admin: number; student: number; top_members: any[] }
  risk_alerts?: { total: number; items: any[] }
  announcements?: { total: number; items: any[] }
  [key: string]: any
}

// ============================================
// 操作日志
// ============================================

/** 操作日志 */
export interface OperationLog {
  id: number
  user?: number
  operator?: number
  user_name?: string
  operator_name?: string
  module?: string
  action?: string
  operation_type?: string
  object_type?: string
  object_id?: string | number | null
  object_repr?: string
  request_method?: string
  request_path?: string
  request_data?: any
  response_status?: number
  ip_address?: string
  request_ip?: string
  user_agent?: string
  description?: string
  created_at: string
}

// ============================================
// 通知
// ============================================

/** 通知 */
export interface Notification {
  id: number
  recipient: number
  recipient_name?: string
  title: string
  content: string
  category?: string
  notification_type?: string
  is_read: boolean
  related_type?: string
  related_object_type?: string
  related_id?: number
  related_object_id?: number
  priority?: string
  channel?: string
  created_at: string
}

// ============================================
// 技能标签与成员技能
// ============================================

/** 技能标签 */
export interface SkillTag {
  id: number
  name: string
  category?: string
  created_at?: string
}

/** 成员技能 */
export interface MemberSkill {
  id: number
  user: number
  user_name?: string
  skill_tag: number
  skill_tag_name?: string
  proficiency: number
  created_at?: string
}

// ============================================
// 灵活工作时间
// ============================================

/** 灵活工作时间 */
export interface FlexibleWorkSchedule {
  id: number
  user: number
  user_name?: string
  period_start: string
  period_end: string
  available_hours?: number
  work_hours?: number
  can_offline: boolean
  can_urgent: boolean
  is_saturated: boolean
  remark?: string
  created_at: string
}

// ============================================
// 贡献记录
// ============================================

export type ContributionType =
  | 'task_complete'
  | 'project_lead'
  | 'competition'
  | 'finance_manage'
  | 'file_upload'
  | 'ip_writing'
  | 'ip_execution'
  | 'ip_return_fix'
  | 'ip_archive'
  | 'ip_material'
  | 'project_leader'
  | 'core'
  | 'long_term'
  | 'stage_task'
  | 'resource'
  | 'temporary_help'
  | 'nominal'
  | 'exited_contribution'
  | 'other'

/** 贡献记录 */
export interface Contribution {
  id: number
  project: number
  project_name?: string
  user: number
  user_name?: string
  contribution_type: ContributionType
  content: string
  period?: string
  evidence_file?: string
  proof_file?: number | null
  proof_file_name?: string
  status: string
  weight?: number
  reviewer?: number
  reviewer_name?: string
  review_comment?: string
  review_opinion?: string
  reviewed_at?: string
  created_at: string
  updated_at: string
}

// ============================================
// 成员排序
// ============================================

/** 成员排序 */
export interface MemberRanking {
  id: number
  project: number
  user: number
  user_name?: string
  rank: number
  score?: number
  total_score?: number
  period: string
  contribution_count?: number
  task_completed_count: number
  ip_contribution_count: number
  status: string
  is_public?: boolean
  rule_version?: string
  rule_snapshot?: Record<string, any>
  score_snapshot?: {
    period?: string
    total_score?: string
    evidence_count?: number
    breakdown?: Record<string, string>
    evidence?: Array<Record<string, any>>
    manual_overrides?: Array<Record<string, any>>
    objection_adjustments?: Array<Record<string, any>>
  }
  generated_at?: string | null
  confirmed_at?: string | null
  confirmed_by?: number | null
  user_detail?: any
  created_at?: string
  updated_at?: string
}

/** 排序异议 */
export interface RankingObjection {
  id: number
  project: number
  objector: number
  objector_name?: string
  ranking?: number
  ranking_user_name?: string
  content: string
  status: string
  status_display?: string
  objection_status?: string
  leader_opinion?: string
  leader_reviewer?: number
  leader_reviewer_name?: string
  leader_reviewed_at?: string
  teacher_opinion?: string
  teacher_confirmer?: number
  teacher_confirmer_name?: string
  teacher_confirmed_at?: string
  final_result?: string
  original_rank?: number | null
  corrected_rank?: number | null
  original_total_score?: number | string | null
  corrected_total_score?: number | string | null
  adjustment_snapshot?: Record<string, any>
  adjustment_applied_at?: string | null
  adjustment_applied_by?: number | null
  created_at: string
  updated_at?: string
}

// ============================================
// 敏感资料
// ============================================

/** 敏感资料 */
export interface SensitiveData {
  id: number
  user?: number
  user_name?: string
  data_type: string
  data_type_display?: string
  label?: string
  title?: string
  display_name?: string
  masked_value?: string
  owner_name?: string
  project?: number | null
  project_name?: string
  has_file?: boolean
  file_attachment_name?: string
  key_version?: number
  is_encrypted?: boolean
  created_at?: string
  updated_at?: string
}

/** 敏感资料访问申请 */
export interface SensitiveAccessRequest {
  id: number
  requester?: number
  applicant?: number
  requester_name?: string
  applicant_name?: string
  target_user?: number
  sensitive_data?: number
  target_user_name?: string
  data_type?: string
  sensitive_data_type?: string
  sensitive_data_type_display?: string
  sensitive_data_title?: string
  use_scenario?: string
  usage_scenario?: string
  reason: string
  project?: number
  project_name?: string
  expected_use_time?: string
  need_download?: boolean
  is_download: boolean
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  status_display?: string
  is_accessible?: boolean
  has_attachment?: boolean
  attachment_name?: string
  can_download_attachment?: boolean
  valid_duration?: number
  approver?: number
  approver_name?: string
  approve_comment?: string
  approval_opinion?: string
  reject_comment?: string
  approved_at?: string
  expires_at?: string
  access_expires_at?: string
  viewed_at?: string
  created_at: string
}

export interface SensitiveDataQueryParams extends PaginationParams {
  project?: number
  data_type?: string
}

export interface SensitiveAccessRequestCreateParams {
  sensitive_data: number
  reason?: string
  usage_scenario: string
  project?: number
  expected_use_time?: string
  is_download: boolean
  request_note?: string
}

export interface SensitiveAccessRequestReviewParams {
  action: 'approve' | 'reject'
  approval_opinion?: string
  expire_hours?: number
}

// ============================================
// 第三方集成
// ============================================

/** 集成配置 */
export interface IntegrationConfig {
  id: number
  name: string
  provider: string
  webhook_url?: string
  app_id?: string
  app_secret?: string
  is_enabled: boolean
  created_at?: string
  updated_at?: string
}

/** 集成日志 */
export interface IntegrationLog {
  id: number
  config: number
  config_name?: string
  event_type: string
  status: string
  message?: string
  request_data?: any
  response_data?: any
  created_at: string
}
