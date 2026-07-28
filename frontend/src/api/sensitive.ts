import { download, get, post } from './request'
import type {
  PaginatedResponse,
  PaginationParams,
  SensitiveAccessRequest,
  SensitiveAccessRequestCreateParams,
  SensitiveAccessRequestReviewParams,
  SensitiveData,
  SensitiveDataCreateParams,
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
): Promise<SensitiveData> => post(`${BASE}/data/`, data)

/** 获取我的敏感资料 */
export const getMySensitiveData = (): Promise<PaginatedResponse<SensitiveData> | SensitiveData[]> =>
  get(`${BASE}/data/my_data/`)

/** 查看敏感资料明文（限时） */
export const viewSensitiveData = (id: number, requestId?: number) =>
  post(`${BASE}/data/${id}/view/`, { request_id: requestId })

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
