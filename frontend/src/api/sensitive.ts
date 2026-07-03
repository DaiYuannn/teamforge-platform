import request from './request'

// 敏感资料模块基础路径
const BASE = '/sensitive'

// ============================================
// 敏感资料 API
// ============================================

/** 获取敏感资料列表 */
export const getSensitiveData = (params?: any) => request.get(`${BASE}/data/`, { params })

/** 创建敏感资料 */
export const createSensitiveData = (data: any) => request.post(`${BASE}/data/`, data)

/** 获取我的敏感资料 */
export const getMySensitiveData = () => request.get(`${BASE}/data/my_data/`)

/** 查看敏感资料明文（限时） */
export const viewSensitiveData = (id: number, requestId?: number) => request.post(`${BASE}/data/${id}/view/`, { request_id: requestId })

// ============================================
// 访问申请 API
// ============================================

/** 获取访问申请列表 */
export const getAccessRequests = (params?: any) => request.get(`${BASE}/requests/`, { params })

/** 创建访问申请 */
export const createAccessRequest = (data: any) => request.post(`${BASE}/requests/`, data)

/** 批准访问申请 */
export const approveAccessRequest = (id: number, data: any) => request.post(`${BASE}/requests/${id}/approve/`, data)

/** 驳回访问申请 */
export const rejectAccessRequest = (id: number, data: any) => request.post(`${BASE}/requests/${id}/reject/`, data)

/** 获取我的访问申请 */
export const getMyAccessRequests = () => request.get(`${BASE}/requests/my_requests/`)

/** 获取待我审批的访问申请 */
export const getPendingApproveRequests = () => request.get(`${BASE}/requests/pending_approve/`)

/** 通过申请查看敏感资料明文 */
export const viewAccessRequestData = (id: number) => request.post(`${BASE}/requests/${id}/view_data/`)
