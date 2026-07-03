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

// 用户
export interface User {
  id: number
  username: string
  email: string
  name: string
  real_name?: string
  global_role: string
  global_role_display?: string
  role?: UserRole
  avatar?: string
  phone?: string
  is_active: boolean
  date_joined: string
  last_login?: string
}

// 登录请求参数
export interface LoginParams {
  email: string
  password: string
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
  real_name?: string
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
export type ProjectStatus = string

// 项目
export interface Project {
  id: number
  name: string
  code: string
  intro: string
  description?: string
  competition?: number | null
  competition_name?: string
  leader: number
  leader_name?: string
  current_stage?: number
  current_stage_display?: string
  status: string
  status_display?: string
  priority?: string
  priority_display?: string
  start_date: string
  planned_end_date: string
  expected_end_date?: string
  actual_end_date?: string | null
  last_leader_update?: string | null
  created_at: string
  updated_at: string
  member_count?: number
  task_count?: number
}

// 项目创建/更新参数
export interface ProjectFormData {
  name: string
  code: string
  description?: string
  competition?: number | null
  leader: number
  start_date: string
  expected_end_date: string
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
  joined_at: string
}

// 添加项目成员参数
export interface AddMemberParams {
  user: number
  role_in_project: string
}

// 阶段流转日志
export interface StageLog {
  id: number
  project: number
  from_stage: ProjectStage | null
  to_stage: ProjectStage
  operator: number
  operator_name: string
  remark: string
  created_at: string
}

// ============================================
// 比赛
// ============================================

// 比赛级别
export type CompetitionLevel = 'national' | 'provincial' | 'municipal' | 'school' | 'enterprise'

// 比赛状态
export type CompetitionStatus = 'upcoming' | 'registering' | 'ongoing' | 'judging' | 'completed'

// 比赛
export interface Competition {
  id: number
  name: string
  level: CompetitionLevel
  level_display?: string
  status: CompetitionStatus
  status_display?: string
  description?: string
  comp_type?: string
  organizer: string
  start_date?: string
  end_date?: string
  register_date?: string
  material_deadline?: string
  review_date?: string
  defense_date?: string
  registration_deadline?: string
  website?: string
  created_at: string
  updated_at: string
}

// 比赛创建/更新参数
export interface CompetitionFormData {
  name: string
  level: CompetitionLevel
  status: CompetitionStatus
  description?: string
  organizer: string
  start_date?: string
  end_date?: string
  registration_deadline?: string
  website?: string
}

// ============================================
// 任务
// ============================================

// 任务状态
export type TaskStatus = string

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
  status: string
  priority?: TaskPriority
  start_date?: string
  deadline: string
  due_date?: string
  delay_reason?: string
  completed_at?: string | null
  created_at: string
  updated_at: string
}

// 任务创建/更新参数
export interface TaskFormData {
  title: string
  description?: string
  project: number
  assignee: number
  status?: string
  priority?: TaskPriority
  start_date?: string
  deadline: string
  due_date?: string
}

// 任务查询参数
export interface TaskQueryParams extends PaginationParams {
  project?: number
  status?: TaskStatus
  assignee?: number
}

// ============================================
// 经费
// ============================================

// 经费类别
export type FinanceCategory = 'registration' | 'material' | 'travel' | 'equipment' | 'labor' | 'other'

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
  category?: string
  amount: number
  title: string
  description?: string
  spender?: number
  spender_name?: string
  reviewer_name?: string
  expense_date?: string
  purpose?: string
  remark?: string
  status: 'pending' | 'approved' | 'rejected' | 'reimbursed'
  approver?: number | null
  approved_at?: string | null
  created_at: string
  updated_at: string
}

// 经费支出创建/更新参数
export interface FinanceExpenseFormData {
  project: number
  category: FinanceCategory
  amount: number
  description: string
  expense_date: string
  remark?: string
}

// 经费票据
export interface FinanceReceipt {
  id: number
  expense: number
  file?: string
  file_name?: string
  file_size?: number
  uploaded_at?: string
  uploaded_by?: number
  uploaded_by_name?: string
  created_at?: string
}

// ============================================
// 文件管理
// ============================================

// 文件权限级别
export type FilePermission = 'public' | 'internal' | 'sensitive'

// 文件资源
export interface FileAsset {
  id: number
  project: number
  project_name?: string
  name: string
  file: string
  file_url?: string
  file_type?: string
  content_type?: string
  file_size?: number
  size?: number
  level?: FilePermission
  level_display?: string
  uploader: number
  uploader_name: string
  version?: number
  description?: string
  created_at: string
  updated_at?: string
}

// 文件上传参数
export interface FileUploadParams {
  project: number
  level: FilePermission
  description?: string
}

// 文件查询参数
export interface FileQueryParams extends PaginationParams {
  project?: number
  file_type?: string
  level?: FilePermission
}

// ============================================
// 导入中心
// ============================================

// 导入模块
export type ImportModule = 'users' | 'projects' | 'members' | 'tasks' | 'competitions'

// 导入任务状态
export type ImportTaskStatus = 'pending' | 'previewing' | 'confirming' | 'completed' | 'failed' | 'rolled_back'

// 导入任务
export interface ImportTask {
  id: number
  module: ImportModule
  file_name: string
  status: ImportTaskStatus
  total_rows: number
  success_rows: number
  failed_rows: number
  error_messages?: string[]
  field_mapping?: Record<string, string>
  operator: number
  operator_name: string
  created_at: string
  completed_at?: string | null
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
  task_id: string
  headers: string[]
  field_mapping: FieldMapping
  preview_rows: Record<string, any>[]
  total_rows: number
  valid_rows: number
  error_rows: number
  error_details: Record<string, any>
  available_fields?: string[]
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
  is_student?: boolean
  grade?: string
  major?: string
  student_id?: string
  department?: string
  position?: string
  project_count?: number
  task_count?: number
  projects?: { project_id: number; project_name: string; project_code: string; role_in_project: string; role_in_project_display: string; project_status: string }[]
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

/** 贡献记录 */
export interface Contribution {
  id: number
  project: number
  project_name?: string
  user: number
  user_name?: string
  contribution_type: string
  content: string
  evidence_file?: string
  proof_file?: string
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
  contribution_count?: number
  task_completed_count: number
  ip_contribution_count: number
  status: string
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
  objection_type?: string
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
  created_at: string
  updated_at?: string
}

// ============================================
// 敏感资料
// ============================================

/** 敏感资料 */
export interface SensitiveData {
  id: number
  user: number
  user_name?: string
  data_type: string
  label: string
  title?: string
  display_name?: string
  masked_value?: string
  owner_name?: string
  is_encrypted?: boolean
  created_at?: string
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
  data_type: string
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
  is_download?: boolean
  status?: string
  valid_duration?: number
  approver?: number
  approver_name?: string
  approve_comment?: string
  approval_opinion?: string
  reject_comment?: string
  approved_at?: string
  expires_at?: string
  access_expires_at?: string
  created_at: string
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
