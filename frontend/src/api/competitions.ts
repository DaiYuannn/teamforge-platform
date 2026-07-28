import { get, post, patch, del, download } from './request'
import type {
  Competition,
  CompetitionFormData,
  CompetitionParticipant,
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

/** 获取比赛负责人和参赛成员名单 */
export function getCompetitionParticipants(id: number): Promise<CompetitionParticipant[]> {
  return get<CompetitionParticipant[]>(`/competitions/${id}/participants/`)
}

/** 添加比赛负责人或参赛成员 */
export function addCompetitionParticipant(
  id: number,
  data: Pick<CompetitionParticipant, 'user' | 'role'> &
    Partial<Pick<CompetitionParticipant, 'participation_status' | 'responsibility'>>,
): Promise<CompetitionParticipant> {
  return post<CompetitionParticipant>(`/competitions/${id}/participants/`, data)
}

/** 更新比赛名单中的角色、状态或分工 */
export function updateCompetitionParticipant(
  id: number,
  participantId: number,
  data: Partial<Pick<CompetitionParticipant, 'role' | 'participation_status' | 'responsibility'>>,
): Promise<CompetitionParticipant> {
  return patch<CompetitionParticipant>(`/competitions/${id}/participants/`, {
    participant_id: participantId,
    ...data,
  })
}

/** 从比赛名单中移除成员 */
export function deleteCompetitionParticipant(id: number, participantId: number): Promise<void> {
  return del<void>(`/competitions/${id}/participants/?participant_id=${participantId}`)
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
