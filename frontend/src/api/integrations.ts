import request from './request'

// 第三方集成模块基础路径
const BASE = '/integrations'

// ============================================
// 集成配置 API
// ============================================

/** 获取集成配置列表 */
export const getIntegrationConfigs = () => request.get(`${BASE}/configs/`)

/** 创建集成配置 */
export const createIntegrationConfig = (data: any) => request.post(`${BASE}/configs/`, data)

/** 更新集成配置 */
export const updateIntegrationConfig = (id: number, data: any) => request.patch(`${BASE}/configs/${id}/`, data)

/** 删除集成配置 */
export const deleteIntegrationConfig = (id: number) => request.delete(`${BASE}/configs/${id}/`)

// ============================================
// 集成日志 API
// ============================================

/** 获取集成日志列表 */
export const getIntegrationLogs = (params?: any) => request.get(`${BASE}/logs/`, { params })
