import request from './request'
import type {
  IPApplication,
  IPApplicationListItem,
  IPApplicationCandidate,
  IPContributor,
  IPMaterialVersion,
  IPObjection,
  IPPaginatedResponse,
  IPReturnRecord,
  IPTodoResponse,
} from '@/types/intellectualProperty'

const BASE = '/intellectual-property'

// ============================================
// 申请档案
// ============================================

/** 获取知识产权申请列表 */
export const getIPApplications = (params?: Record<string, unknown>): Promise<IPPaginatedResponse<IPApplicationListItem>> =>
  request.get(`${BASE}/applications/`, { params })

/** 获取知识产权申请详情 */
export const getIPApplication = (id: number): Promise<IPApplication> => request.get(`${BASE}/applications/${id}/`)

/** 创建知识产权申请 */
export const createIPApplication = (data: Record<string, unknown>): Promise<IPApplication> => request.post(`${BASE}/applications/`, data)

/** 更新知识产权申请 */
export const updateIPApplication = (id: number, data: Record<string, unknown>): Promise<IPApplication> =>
  request.patch(`${BASE}/applications/${id}/`, data)

/** 上传或替换最终授权/登记证书 */
export const uploadIPFinalCertificate = (id: number, file: File): Promise<IPApplication> => {
  const data = new FormData()
  data.append('final_certificate_upload', file)
  return request.patch(`${BASE}/applications/${id}/`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 删除知识产权申请 */
export const deleteIPApplication = (id: number): Promise<any> => request.delete(`${BASE}/applications/${id}/`)

/** 状态流转 */
export const transitionIPStatus = (id: number, data: { target_status: string; note?: string }): Promise<IPApplication> =>
  request.post(`${BASE}/applications/${id}/transition/`, data)

/** 归档 */
export const archiveIPApplication = (id: number): Promise<IPApplication> => request.post(`${BASE}/applications/${id}/archive/`)

/** 同步贡献记录 */
export const syncIPContribution = (id: number): Promise<{ synced_count: number }> => request.post(`${BASE}/applications/${id}/sync_contribution/`)

/** 获取我的待办 */
export const getMyIPTodo = (): Promise<IPTodoResponse> => request.get(`${BASE}/applications/my_todo/`)

/** 获取拟申报/正式提交名单；接口不会返回身份证等敏感明文。 */
export const getIPCandidates = (applicationId: number): Promise<IPApplicationCandidate[]> =>
  request.get(`${BASE}/applications/${applicationId}/candidates/`)

/** 添加拟申报成员。 */
export const addIPCandidate = (
  applicationId: number,
  data: Pick<IPApplicationCandidate, 'user' | 'legal_role'> &
    Partial<Pick<IPApplicationCandidate, 'planned_order' | 'status' | 'identity_check_status' | 'note'>>,
): Promise<IPApplicationCandidate> =>
  request.post(`${BASE}/applications/${applicationId}/candidates/`, data)

/** 更新名单状态、署名顺序或身份核验结果。 */
export const updateIPCandidate = (
  applicationId: number,
  candidateId: number,
  data: Partial<Pick<IPApplicationCandidate, 'legal_role' | 'planned_order' | 'status' | 'identity_check_status' | 'note'>>,
): Promise<IPApplicationCandidate> =>
  request.patch(`${BASE}/applications/${applicationId}/candidates/`, {
    candidate_id: candidateId,
    ...data,
  })

/** 移除拟申报名单记录。 */
export const deleteIPCandidate = (applicationId: number, candidateId: number): Promise<any> =>
  request.delete(`${BASE}/applications/${applicationId}/candidates/`, {
    params: { candidate_id: candidateId },
  })

// ============================================
// 责任分工
// ============================================

/** 获取责任分工列表 */
export const getIPContributors = (applicationId: number): Promise<IPPaginatedResponse<IPContributor>> =>
  request.get(`${BASE}/contributors/`, { params: { application: applicationId } })

/** 添加贡献者 */
export const addIPContributor = (applicationId: number, data: Record<string, unknown>): Promise<IPContributor> =>
  request.post(`${BASE}/contributors/`, { ...data, application: applicationId })

/** 更新贡献者 */
export const updateIPContributor = (id: number, data: Record<string, unknown>): Promise<IPContributor> =>
  request.patch(`${BASE}/contributors/${id}/`, data)

/** 贡献人确认本人贡献记录 */
export const confirmIPContributor = (id: number): Promise<IPContributor> =>
  request.post(`${BASE}/contributors/${id}/confirm/`)

// ============================================
// 材料版本
// ============================================

/** 获取材料版本列表 */
export const getIPMaterials = (applicationId: number): Promise<IPPaginatedResponse<IPMaterialVersion>> =>
  request.get(`${BASE}/materials/`, { params: { application: applicationId } })

/** 上传材料版本 */
export const uploadIPMaterial = (applicationId: number, data: FormData): Promise<any> => {
  data.append('application', String(applicationId))
  return request.post(`${BASE}/materials/`, data, { headers: { 'Content-Type': 'multipart/form-data' } })
}

/** 更新材料版本属性（包括最终版标记） */
export const updateIPMaterial = (
  id: number,
  data: Partial<Pick<IPMaterialVersion, 'material_type' | 'version' | 'change_note' | 'is_final'>>,
): Promise<IPMaterialVersion> => request.patch(`${BASE}/materials/${id}/`, data)

// ============================================
// 退回记录
// ============================================

/** 获取退回记录列表 */
export const getIPReturns = (applicationId: number): Promise<IPPaginatedResponse<IPReturnRecord>> =>
  request.get(`${BASE}/returns/`, { params: { application: applicationId } })

/** 创建退回记录 */
export const createIPReturn = (applicationId: number, data: Record<string, unknown>): Promise<IPReturnRecord> =>
  request.post(`${BASE}/returns/`, { ...data, application: applicationId })

/** 解决退回记录 */
export const resolveIPReturn = (id: number, data: { modify_description: string; result: string }): Promise<IPReturnRecord> =>
  request.post(`${BASE}/returns/${id}/resolve/`, data)

// ============================================
// 异议
// ============================================

/** 获取异议列表 */
export const getIPObjections = (applicationId: number): Promise<IPPaginatedResponse<IPObjection>> =>
  request.get(`${BASE}/objections/`, { params: { application: applicationId } })

/** 创建异议 */
export const createIPObjection = (applicationId: number, data: FormData | Record<string, unknown>): Promise<IPObjection> => {
  if (data instanceof FormData) {
    data.append('application', String(applicationId))
    return request.post(`${BASE}/objections/`, data, { headers: { 'Content-Type': 'multipart/form-data' } })
  }
  return request.post(`${BASE}/objections/`, { ...data, application: applicationId })
}

/** 审核异议 */
export type IPObjectionReviewPayload =
  | { action: 'leader_review'; leader_opinion: string }
  | {
      action: 'teacher_confirm'
      teacher_opinion: string
      final_result: string
      final_status: 'resolved' | 'rejected'
    }

export const reviewIPObjection = (id: number, data: IPObjectionReviewPayload): Promise<IPObjection> =>
  request.patch(`${BASE}/objections/${id}/review/`, data)
