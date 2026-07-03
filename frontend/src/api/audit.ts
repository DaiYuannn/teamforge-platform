import request from './request'

// 操作日志模块基础路径
const BASE = '/audit'

// ============================================
// 操作日志 API
// ============================================

/** 获取操作日志列表 */
export const getOperationLogs = (params?: any) => request.get(`${BASE}/operation-logs/`, { params })

/** 获取操作日志详情 */
export const getOperationLog = (id: number) => request.get(`${BASE}/operation-logs/${id}/`)

/** 获取模块操作统计 */
export const getModuleStats = () => request.get(`${BASE}/operation-logs/module_stats/`)

/** 获取最近操作日志 */
export const getRecentLogs = (params?: any) => request.get(`${BASE}/operation-logs/recent/`, { params })
