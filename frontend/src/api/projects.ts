import { get, post, patch, del } from './request'
import type {
  Project,
  ProjectFormData,
  ProjectMember,
  StageLog,
  AdvanceStageParams,
  AddMemberParams,
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

/** 获取阶段流转日志 */
export function getStageLogs(id: number): Promise<StageLog[]> {
  return get<StageLog[]>(`/projects/${id}/stage_logs/`)
}
