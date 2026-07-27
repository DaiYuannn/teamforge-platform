import { get, post, patch, del } from './request'
import type {
  Project,
  ProjectFormData,
  ProjectMember,
  StageLog,
  AdvanceStageParams,
  AddMemberParams,
  ProjectMembershipEvent,
  PaginatedResponse,
  PaginationParams,
} from '@/types'

/** 项目查询参数 */
export interface ProjectQueryParams extends PaginationParams {
  status?: string
  leader?: number | string
  competition?: number
  current_stage?: string
  start_date?: string
  end_date?: string
  scope?: 'mine' | 'team'
}

/** 获取项目列表 */
export function getProjects(params: ProjectQueryParams): Promise<PaginatedResponse<Project>> {
  return get<PaginatedResponse<Project>>('/projects/', params)
}

/** 获取项目详情 */
export function getProject(id: number): Promise<Project> {
  return get<Project>(`/projects/${id}/`)
}

/** 创建项目 */
export function createProject(data: ProjectFormData): Promise<Project> {
  return post<Project>('/projects/', data)
}

/** 更新项目 */
export function updateProject(id: number, data: Partial<ProjectFormData>): Promise<Project> {
  return patch<Project>(`/projects/${id}/`, data)
}

/** 删除项目 */
export function deleteProject(id: number): Promise<void> {
  return del<void>(`/projects/${id}/`)
}

/** 阶段流转（推进到下一阶段） */
export function advanceStage(id: number, data: AdvanceStageParams): Promise<Project> {
  return post<Project>(`/projects/${id}/stage/`, { to_stage: data.target_stage, note: data.remark })
}

/** 负责人更新（仅项目负责人可用） */
export function leaderUpdate(id: number, note: string): Promise<Project> {
  return post<Project>(`/projects/${id}/leader_update/`, { note })
}

/** 获取项目成员列表 */
export function getProjectMembers(id: number): Promise<ProjectMember[]> {
  return get<ProjectMember[]>(`/projects/${id}/members/`)
}

/** 添加项目成员 */
export function addProjectMember(id: number, data: AddMemberParams): Promise<ProjectMember> {
  return post<ProjectMember>(`/projects/${id}/members/`, { user_id: data.user, role_in_project: data.role_in_project })
}

/** 移除项目成员 */
export function removeProjectMember(id: number, userId: number): Promise<void> {
  return del<void>(`/projects/${id}/members/?user_id=${userId}`)
}

export function updateProjectMember(
  id: number,
  data: {
    member_id: number
    role_in_project?: string
    status?: string
    reason?: string
    handover_to?: number
    handover_notes?: string
  },
): Promise<ProjectMember> {
  return patch<ProjectMember>(`/projects/${id}/members/`, data)
}

export function getProjectMembershipHistory(
  id: number,
  userId?: number,
): Promise<ProjectMembershipEvent[]> {
  return get<ProjectMembershipEvent[]>(
    `/projects/${id}/membership-history/`,
    userId ? { user_id: userId } : undefined,
  )
}

/** 获取阶段流转日志 */
export function getStageLogs(id: number): Promise<StageLog[]> {
  return get<StageLog[]>(`/projects/${id}/stage_logs/`)
}

export interface Milestone {
  id: number
  project: number
  project_name: string
  title: string
  description: string
  due_date: string | null
  is_completed: boolean
  completed_at: string | null
  sort_order: number
  created_at: string
}

export interface MilestoneInput {
  project: number
  title: string
  description?: string
  due_date?: string | null
  sort_order?: number
}

export function getMilestones(params: PaginationParams & { project?: number; is_completed?: boolean }) {
  return get<PaginatedResponse<Milestone>>('/projects/milestones/', params)
}

export function createMilestone(data: MilestoneInput): Promise<Milestone> {
  return post<Milestone>('/projects/milestones/', data)
}

export function updateMilestone(id: number, data: Partial<MilestoneInput>): Promise<Milestone> {
  return patch<Milestone>(`/projects/milestones/${id}/`, data)
}

export function deleteMilestone(id: number): Promise<void> {
  return del<void>(`/projects/milestones/${id}/`)
}

export function toggleMilestone(id: number): Promise<Milestone> {
  return post<Milestone>(`/projects/milestones/${id}/toggle/`)
}

export type ProjectRiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type ProjectRiskStatus = 'open' | 'mitigating' | 'closed'

export interface ProjectRisk {
  id: number
  project: number
  project_name: string
  title: string
  description: string
  level: ProjectRiskLevel
  level_display: string
  status: ProjectRiskStatus
  status_display: string
  mitigation_plan: string
  identified_by: number
  identified_by_name: string
  identified_at: string
  resolved_at: string | null
}

export interface ProjectRiskInput {
  project: number
  title: string
  description?: string
  level: ProjectRiskLevel
  status?: ProjectRiskStatus
  mitigation_plan?: string
}

export function getProjectRisks(
  params: PaginationParams & { project?: number; level?: ProjectRiskLevel; status?: ProjectRiskStatus },
) {
  return get<PaginatedResponse<ProjectRisk>>('/projects/risks/', params)
}

export function createProjectRisk(data: ProjectRiskInput): Promise<ProjectRisk> {
  return post<ProjectRisk>('/projects/risks/', data)
}

export function updateProjectRisk(id: number, data: Partial<ProjectRiskInput>): Promise<ProjectRisk> {
  return patch<ProjectRisk>(`/projects/risks/${id}/`, data)
}

export function deleteProjectRisk(id: number): Promise<void> {
  return del<void>(`/projects/risks/${id}/`)
}

export function resolveProjectRisk(id: number): Promise<ProjectRisk> {
  return post<ProjectRisk>(`/projects/risks/${id}/resolve/`)
}

export interface ProjectTemplateConfig {
  milestones?: Array<Pick<MilestoneInput, 'title' | 'description' | 'due_date' | 'sort_order'>>
  tasks?: Array<{ title: string; description?: string; priority?: string }>
  [key: string]: unknown
}

export interface ProjectTemplate {
  id: number
  name: string
  description: string
  category: string
  config: ProjectTemplateConfig
  created_by: number
  created_by_name: string
  is_active: boolean
  created_at: string
}

export interface ProjectTemplateInput {
  name: string
  description?: string
  category?: string
  config: ProjectTemplateConfig
  is_active?: boolean
}

export interface InstantiateProjectInput {
  name: string
  code: string
  leader: number
  intro?: string
  priority?: string
  start_date?: string | null
  planned_end_date?: string | null
}

export type InstantiatedProject = Project & {
  _instantiated?: { milestones: number; tasks: number }
}

export function getProjectTemplates(params: PaginationParams & { category?: string; is_active?: boolean }) {
  return get<PaginatedResponse<ProjectTemplate>>('/projects/templates/', params)
}

export function createProjectTemplate(data: ProjectTemplateInput): Promise<ProjectTemplate> {
  return post<ProjectTemplate>('/projects/templates/', data)
}

export function updateProjectTemplate(
  id: number,
  data: Partial<ProjectTemplateInput>,
): Promise<ProjectTemplate> {
  return patch<ProjectTemplate>(`/projects/templates/${id}/`, data)
}

export function deleteProjectTemplate(id: number): Promise<void> {
  return del<void>(`/projects/templates/${id}/`)
}

export function instantiateProjectTemplate(
  id: number,
  data: InstantiateProjectInput,
): Promise<InstantiatedProject> {
  return post<InstantiatedProject>(`/projects/templates/${id}/instantiate/`, data)
}

export interface DiscussionReply {
  id: number
  topic: number
  author: number
  author_name: string
  content: string
  parent: number | null
  created_at: string
}

export interface DiscussionTopic {
  id: number
  project: number
  project_name: string
  title: string
  content?: string
  author: number
  author_name: string
  is_pinned: boolean
  is_closed: boolean
  view_count: number
  reply_count: number
  replies?: DiscussionReply[]
  created_at: string
  updated_at: string
}

export interface DiscussionTopicInput {
  project: number
  title: string
  content: string
  is_pinned?: boolean
  is_closed?: boolean
}

export function getDiscussionTopics(params: PaginationParams & { project?: number }) {
  return get<PaginatedResponse<DiscussionTopic>>('/projects/discussions/', params)
}

export function getDiscussionTopic(id: number): Promise<DiscussionTopic> {
  return get<DiscussionTopic>(`/projects/discussions/${id}/`)
}

export function createDiscussionTopic(data: DiscussionTopicInput): Promise<DiscussionTopic> {
  return post<DiscussionTopic>('/projects/discussions/', data)
}

export function updateDiscussionTopic(
  id: number,
  data: Partial<DiscussionTopicInput>,
): Promise<DiscussionTopic> {
  return patch<DiscussionTopic>(`/projects/discussions/${id}/`, data)
}

export function deleteDiscussionTopic(id: number): Promise<void> {
  return del<void>(`/projects/discussions/${id}/`)
}

export function replyDiscussionTopic(
  id: number,
  data: { content: string; parent?: number | null },
): Promise<DiscussionReply> {
  return post<DiscussionReply>(`/projects/discussions/${id}/reply/`, data)
}

export function getDiscussionReplies(id: number): Promise<DiscussionReply[]> {
  return get<DiscussionReply[]>(`/projects/discussions/${id}/replies/`)
}

export function toggleDiscussionPin(id: number): Promise<DiscussionTopic> {
  return post<DiscussionTopic>(`/projects/discussions/${id}/toggle-pin/`)
}

export function toggleDiscussionClose(id: number): Promise<DiscussionTopic> {
  return post<DiscussionTopic>(`/projects/discussions/${id}/toggle-close/`)
}

export type KnowledgeCategory = 'guide' | 'template' | 'faq' | 'experience' | 'other'

export interface KnowledgeArticle {
  id: number
  title: string
  content?: string
  category: KnowledgeCategory
  category_display: string
  project: number | null
  project_name: string
  author: number | null
  author_name: string
  tags: string
  tag_list?: string[]
  view_count: number
  is_published: boolean
  created_at: string
  updated_at?: string
}

export interface KnowledgeArticleInput {
  title: string
  content: string
  category: KnowledgeCategory
  project: number | null
  tags?: string
  is_published?: boolean
}

export function getKnowledgeArticles(
  params: PaginationParams & { project?: number; category?: KnowledgeCategory; tag?: string },
) {
  return get<PaginatedResponse<KnowledgeArticle>>('/projects/knowledge/', params)
}

export function getKnowledgeArticle(id: number): Promise<KnowledgeArticle> {
  return get<KnowledgeArticle>(`/projects/knowledge/${id}/`)
}

export function createKnowledgeArticle(data: KnowledgeArticleInput): Promise<KnowledgeArticle> {
  return post<KnowledgeArticle>('/projects/knowledge/', data)
}

export function updateKnowledgeArticle(
  id: number,
  data: Partial<KnowledgeArticleInput>,
): Promise<KnowledgeArticle> {
  return patch<KnowledgeArticle>(`/projects/knowledge/${id}/`, data)
}

export function deleteKnowledgeArticle(id: number): Promise<void> {
  return del<void>(`/projects/knowledge/${id}/`)
}

export type ProjectReviewStatus = 'draft' | 'submitted' | 'reviewed'

export interface ProjectReview {
  id: number
  project: number
  project_name: string
  status: ProjectReviewStatus
  status_display: string
  summary: string
  achievements: string
  problems: string
  lessons: string
  improvements: string
  team_feedback: string
  overall_score: number | null
  schedule_score: number | null
  budget_score: number | null
  team_score: number | null
  quality_score: number | null
  reviewer: number | null
  reviewer_name: string
  review_date: string | null
  created_at: string
  updated_at: string
}

export type ProjectReviewInput = Pick<ProjectReview,
  | 'project'
  | 'summary'
  | 'achievements'
  | 'problems'
  | 'lessons'
  | 'improvements'
  | 'team_feedback'
  | 'overall_score'
  | 'schedule_score'
  | 'budget_score'
  | 'team_score'
  | 'quality_score'
>

export function getProjectReviews(params: PaginationParams & { project?: number }) {
  return get<PaginatedResponse<ProjectReview>>('/projects/reviews/', params)
}

export function createProjectReview(data: ProjectReviewInput): Promise<ProjectReview> {
  return post<ProjectReview>('/projects/reviews/', data)
}

export function updateProjectReview(
  id: number,
  data: Partial<ProjectReviewInput>,
): Promise<ProjectReview> {
  return patch<ProjectReview>(`/projects/reviews/${id}/`, data)
}

export function deleteProjectReview(id: number): Promise<void> {
  return del<void>(`/projects/reviews/${id}/`)
}

export function submitProjectReview(id: number): Promise<ProjectReview> {
  return post<ProjectReview>(`/projects/reviews/${id}/submit/`)
}

export function approveProjectReview(id: number): Promise<ProjectReview> {
  return post<ProjectReview>(`/projects/reviews/${id}/approve/`)
}

export interface RiskPrediction {
  project_id: number
  project_name: string
  risk_score: number
  risk_level: ProjectRiskLevel
  risk_factors: Array<{
    category: string
    label: string
    severity: ProjectRiskLevel
    score: number
    detail: string
  }>
  recommendations: string[]
  analyzed_at: string
}

export interface HealthScoreCategory {
  label: string
  score: number
  weight: number
  detail: string
}

export interface ProjectHealthScore {
  project_id: number
  project_name: string
  overall_score: number
  grade: 'A' | 'B' | 'C' | 'D'
  category_scores: Record<string, HealthScoreCategory>
  analyzed_at: string
}

export interface SmartReview {
  project_id: number
  project_name: string
  generated_at: string
  summary: string
  achievements: Array<Record<string, unknown>>
  problem_areas: Array<{ area: string; label: string; detail: string }>
  lessons: string[]
  improvements: string[]
  task_statistics: {
    total: number
    done: number
    overdue: number
    cancelled: number
    completion_rate: number
  }
  finance_summary: Record<string, number | boolean>
  team_performance: Array<Record<string, unknown>>
  timeline: Array<Record<string, unknown>>
}

export type MaterialStatus = 'complete' | 'incomplete' | 'missing'

export interface MaterialCheck {
  project_id: number
  project_name: string
  overall_status: MaterialStatus
  completed_count: number
  total_count: number
  completion_rate: number
  checklist: Array<{ key: string; label: string; status: MaterialStatus; detail: string }>
}

export function getRiskPrediction(projectId: number): Promise<RiskPrediction> {
  return get<RiskPrediction>('/projects/risk-prediction/', { project_id: projectId })
}

export function getProjectHealthScore(projectId: number): Promise<ProjectHealthScore> {
  return get<ProjectHealthScore>('/projects/health-score/', { project_id: projectId })
}

export function getSmartReview(projectId: number): Promise<SmartReview> {
  return get<SmartReview>('/projects/smart-review/', { project_id: projectId })
}

export function getMaterialCheck(projectId: number): Promise<MaterialCheck> {
  return get<MaterialCheck>('/projects/material-check/', { project_id: projectId })
}
