import { get, post, patch, del } from './request'
import type { Competition, CompetitionFormData, PaginatedResponse, PaginationParams } from '@/types'

/** 比赛查询参数 */
export interface CompetitionQueryParams extends PaginationParams {
  level?: string
  status?: string
  project?: number
}

/** 获取比赛列表 */
export function getCompetitions(params: CompetitionQueryParams): Promise<PaginatedResponse<Competition>> {
  return get<PaginatedResponse<Competition>>('/competitions/', params)
}

/** 获取比赛详情 */
export function getCompetition(id: number): Promise<Competition> {
  return get<Competition>(`/competitions/${id}/`)
}

/** 创建比赛 */
export function createCompetition(data: CompetitionFormData): Promise<Competition> {
  return post<Competition>('/competitions/', data)
}

/** 更新比赛 */
export function updateCompetition(id: number, data: Partial<CompetitionFormData>): Promise<Competition> {
  return patch<Competition>(`/competitions/${id}/`, data)
}

/** 删除比赛 */
export function deleteCompetition(id: number): Promise<void> {
  return del<void>(`/competitions/${id}/`)
}
