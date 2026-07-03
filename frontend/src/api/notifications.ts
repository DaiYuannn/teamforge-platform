import request from './request'

// 通知模块基础路径（后端路由注册为空前缀，直接挂在 /api/v1/notifications/ 下）
const BASE = '/notifications'

// ============================================
// 通知中心 API
// ============================================

/** 获取通知列表 */
export const getNotifications = (params?: any) => request.get(`${BASE}/`, { params })

/** 标记单条通知为已读 */
export const markAsRead = (id: number) => request.post(`${BASE}/${id}/mark_as_read/`)

/** 标记全部通知为已读 */
export const markAllAsRead = () => request.post(`${BASE}/mark_all_as_read/`)

/** 获取未读通知数量 */
export const getUnreadCount = () => request.get(`${BASE}/unread_count/`)
