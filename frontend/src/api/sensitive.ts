import { download, get, post, upload } from './request'
import type {
  PaginatedResponse,
  PaginationParams,
  SensitiveAccessRequest,
  SensitiveAccessRequestCreateParams,
  SensitiveAccessRequestReviewParams,
  SensitiveData,
  SensitiveDataCreateParams,
  SensitiveDataGrant,
  SensitiveGrantAccessLog,
  SensitiveDataQueryParams,
} from '@/types'

// 敏感资料模块基础路径
const BASE = '/sensitive'

// ============================================
// 敏感资料 API
// ============================================

/** 获取敏感资料列表 */
export const getSensitiveData = (
  params?: SensitiveDataQueryParams,
): Promise<PaginatedResponse<SensitiveData> | SensitiveData[]> =>
  get(`${BASE}/data/`, params)

/** 创建敏感资料 */
export const createSensitiveData = (
  data: SensitiveDataCreateParams,
): Promise<SensitiveData> => {
  if (!data.attachment_upload) return post(`${BASE}/data/`, data)
  const formData = new FormData()
  Object.entries(data).forEach(([key, value]) => {
    if (value === undefined || value === null || key === 'attachment_upload') return
    formData.append(key, String(value))
  })
  formData.append('attachment_upload', data.attachment_upload)
  return upload(`${BASE}/data/`, formData)
}

/** 获取我的敏感资料 */
export const getMySensitiveData = (): Promise<PaginatedResponse<SensitiveData> | SensitiveData[]> =>
  get(`${BASE}/data/my_data/`)

/** 查看敏感资料明文（限时） */
export const viewSensitiveData = (id: number, requestId?: number, grantId?: number) =>
  post(`${BASE}/data/${id}/view/`, {
    ...(requestId ? { request_id: requestId } : {}),
    ...(grantId ? { grant_id: grantId } : {}),
  })

export const getSensitiveDataGrants = (id: number): Promise<SensitiveDataGrant[]> =>
  get(`${BASE}/data/${id}/grants/`)

export const saveSensitiveDataGrant = (
  id: number,
  data: Pick<SensitiveDataGrant, 'granted_to' | 'can_view' | 'can_download' | 'purpose' | 'expires_at'>,
): Promise<SensitiveDataGrant> => post(`${BASE}/data/${id}/grants/`, data)

export const revokeSensitiveDataGrant = (id: number, grantId: number): Promise<SensitiveDataGrant> =>
  post(`${BASE}/data/${id}/grants/${grantId}/revoke/`)

export const getSensitiveGrantCandidates = (
  id: number,
  search = '',
): Promise<Array<{ id: number; name: string; email: string; school?: string; major?: string }>> =>
  get(`${BASE}/data/${id}/grant-candidates/`, search ? { search } : undefined)

export const getSensitiveGrantAccessLogs = (id: number): Promise<SensitiveGrantAccessLog[]> =>
  get(`${BASE}/data/${id}/grant-access-logs/`)

export const downloadSensitiveAttachmentByGrant = (
  id: number,
  grantId: number,
): Promise<Blob> => download(`${BASE}/data/${id}/download-by-grant/`, {
  params: { grant_id: grantId },
})

// ============================================
// 访问申请 API
// ============================================

/** 获取访问申请列表 */
export const getAccessRequests = (
  params?: Record<string, unknown>,
): Promise<PaginatedResponse<SensitiveAccessRequest> | SensitiveAccessRequest[]> =>
  get(`${BASE}/requests/`, params)

/** 获取单条访问申请（用于通知深链） */
export const getAccessRequest = (id: number): Promise<SensitiveAccessRequest> =>
  get(`${BASE}/requests/${id}/`)

/** 创建访问申请 */
export const createAccessRequest = (
  data: SensitiveAccessRequestCreateParams,
): Promise<SensitiveAccessRequest> => post(`${BASE}/requests/`, data)

/** 批准访问申请 */
export const approveAccessRequest = (
  id: number,
  data: SensitiveAccessRequestReviewParams,
): Promise<SensitiveAccessRequest> =>
  post(`${BASE}/requests/${id}/approve/`, data)

/** 驳回访问申请 */
export const rejectAccessRequest = (
  id: number,
  data: SensitiveAccessRequestReviewParams,
): Promise<SensitiveAccessRequest> =>
  post(`${BASE}/requests/${id}/reject/`, data)

/** 获取我的访问申请 */
export const getMyAccessRequests = (params?: PaginationParams): Promise<
  PaginatedResponse<SensitiveAccessRequest> | SensitiveAccessRequest[]
> => get(`${BASE}/requests/my_requests/`, params)

/** 获取待我审批的访问申请 */
export const getPendingApproveRequests = (params?: PaginationParams): Promise<
  PaginatedResponse<SensitiveAccessRequest> | SensitiveAccessRequest[]
> => get(`${BASE}/requests/pending_approve/`, params)

/** 通过申请查看敏感资料明文 */
export const viewAccessRequestData = (id: number) =>
  post(`${BASE}/requests/${id}/view_data/`)

/** 申请人依据已批准且仍有效的下载申请获取敏感附件 */
export const downloadSensitiveAttachment = (requestId: number): Promise<Blob> =>
  download(`${BASE}/requests/${requestId}/download-attachment/`)
