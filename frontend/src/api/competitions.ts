import { get, post, patch, del, download } from './request'
import type {
  Competition,
  CompetitionFormData,
  CompetitionLevel,
  CompetitionStatus,
  PaginatedResponse,
  PaginationParams,
} from '@/types'

/** 比赛查询参数 */
export interface CompetitionQueryParams extends PaginationParams {
  level?: CompetitionLevel | ''
  status?: CompetitionStatus | ''
  project?: number
}

/** 导出比赛时沿用列表中的业务筛选，不携带分页参数。 */
export interface CompetitionExportParams {
  search?: string
  level?: CompetitionLevel | ''
  status?: CompetitionStatus | ''
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

/** 将当前比赛筛选导出为 Excel。 */
export function exportCompetitions(params: CompetitionExportParams): Promise<Blob> {
  return download('/exports/', {
    params: {
      type: 'competitions',
      file_format: 'xlsx',
      search: params.search || undefined,
      level: params.level || undefined,
      status: params.status || undefined,
      project_id: params.project,
    },
  })
}
