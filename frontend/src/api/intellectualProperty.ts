import request from './request'
import type { IPApplication, IPApplicationListItem, IPContributor, IPReturnRecord, IPMaterialVersion, IPObjection, IPTodoItem } from '@/types/intellectualProperty'

const BASE = '/intellectual-property'

// ============================================
// 申请档案
// ============================================

/** 获取知识产权申请列表 */
export const getIPApplications = (params?: any): Promise<any> => request.get(`${BASE}/applications/`, { params })

/** 获取知识产权申请详情 */
export const getIPApplication = (id: number): Promise<any> => request.get(`${BASE}/applications/${id}/`)

/** 创建知识产权申请 */
export const createIPApplication = (data: any): Promise<any> => request.post(`${BASE}/applications/`, data)

/** 更新知识产权申请 */
export const updateIPApplication = (id: number, data: any): Promise<any> => request.patch(`${BASE}/applications/${id}/`, data)

/** 删除知识产权申请 */
export const deleteIPApplication = (id: number): Promise<any> => request.delete(`${BASE}/applications/${id}/`)

/** 状态流转 */
export const transitionIPStatus = (id: number, data: { target_status: string; note?: string }): Promise<any> => request.post(`${BASE}/applications/${id}/transition/`, data)

/** 归档 */
export const archiveIPApplication = (id: number, data?: any): Promise<any> => request.post(`${BASE}/applications/${id}/archive/`, data)

/** 同步贡献记录 */
export const syncIPContribution = (id: number): Promise<any> => request.post(`${BASE}/applications/${id}/sync_contribution/`)

/** 获取我的待办 */
export const getMyIPTodo = (): Promise<any> => request.get(`${BASE}/applications/my_todo/`)

// ============================================
// 责任分工
// ============================================

/** 获取责任分工列表 */
export const getIPContributors = (applicationId: number): Promise<any> => request.get(`${BASE}/contributors/`, { params: { application: applicationId } })

/** 添加贡献者 */
export const addIPContributor = (applicationId: number, data: any): Promise<any> => request.post(`${BASE}/contributors/`, { ...data, application: applicationId })

/** 更新贡献者 */
export const updateIPContributor = (id: number, data: any): Promise<any> => request.patch(`${BASE}/contributors/${id}/`, data)

// ============================================
// 材料版本
// ============================================

/** 获取材料版本列表 */
export const getIPMaterials = (applicationId: number): Promise<any> => request.get(`${BASE}/materials/`, { params: { application: applicationId } })

/** 上传材料版本 */
export const uploadIPMaterial = (applicationId: number, data: FormData): Promise<any> => {
  data.append('application', String(applicationId))
  return request.post(`${BASE}/materials/`, data, { headers: { 'Content-Type': 'multipart/form-data' } })
}

// ============================================
// 退回记录
// ============================================

/** 获取退回记录列表 */
export const getIPReturns = (applicationId: number): Promise<any> => request.get(`${BASE}/returns/`, { params: { application: applicationId } })

/** 创建退回记录 */
export const createIPReturn = (applicationId: number, data: any): Promise<any> => request.post(`${BASE}/returns/`, { ...data, application: applicationId })

/** 解决退回记录 */
export const resolveIPReturn = (id: number, data: any): Promise<any> => request.post(`${BASE}/returns/${id}/resolve/`, data)

// ============================================
// 异议
// ============================================

/** 获取异议列表 */
export const getIPObjections = (applicationId: number): Promise<any> => request.get(`${BASE}/objections/`, { params: { application: applicationId } })

/** 创建异议 */
export const createIPObjection = (applicationId: number, data: any): Promise<any> => {
  if (data instanceof FormData) {
    data.append('application', String(applicationId))
    return request.post(`${BASE}/objections/`, data)
  }
  return request.post(`${BASE}/objections/`, { ...data, application: applicationId })
}

/** 审核异议 */
export const reviewIPObjection = (id: number, data: any): Promise<any> => request.patch(`${BASE}/objections/${id}/review/`, data)
