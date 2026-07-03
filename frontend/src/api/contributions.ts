import request from './request'

// 贡献记录模块基础路径
const BASE = '/contributions'

// ============================================
// 贡献记录 API
// ============================================

/** 获取贡献记录列表 */
export const getContributions = (params?: any) => request.get(`${BASE}/contributions/`, { params })

/** 创建贡献记录 */
export const createContribution = (data: any) => request.post(`${BASE}/contributions/`, data)

/** 更新贡献记录 */
export const updateContribution = (id: number, data: any) => request.patch(`${BASE}/contributions/${id}/`, data)

/** 删除贡献记录 */
export const deleteContribution = (id: number) => request.delete(`${BASE}/contributions/${id}/`)

/** 审核贡献记录 */
export const reviewContribution = (id: number, data: any) => request.patch(`${BASE}/contributions/${id}/review/`, data)

/** 获取我的贡献记录 */
export const getMyContributions = () => request.get(`${BASE}/contributions/my_contributions/`)

/** 获取待我审核的贡献记录 */
export const getPendingReview = () => request.get(`${BASE}/contributions/pending_review/`)

/** 按项目获取贡献记录 */
export const getContributionsByProject = (projectId: number) => request.get(`${BASE}/contributions/by_project/`, { params: { project: projectId } })

// ============================================
// 成员排序 API
// ============================================

/** 获取排序列表 */
export const getRankings = (params?: any) => request.get(`${BASE}/rankings/`, { params })

/** 生成排序（项目负责人） */
export const generateRanking = (projectId: number) => request.post(`${BASE}/rankings/generate/`, { project: projectId })

/** 更新排名（拖拽或输入修改） */
export const updateRank = (id: number, data: any) => request.patch(`${BASE}/rankings/${id}/update_rank/`, data)

/** 确认排序（老师） */
export const confirmRanking = (projectId: number) => request.post(`${BASE}/rankings/confirm/`, { project: projectId })

/** 按项目获取排序 */
export const getRankingsByProject = (projectId: number) => request.get(`${BASE}/rankings/by_project/`, { params: { project: projectId } })

// ============================================
// 排序异议 API
// ============================================

/** 获取异议列表 */
export const getObjections = (params?: any) => request.get(`${BASE}/objections/`, { params })

/** 创建异议 */
export const createObjection = (data: any) => request.post(`${BASE}/objections/`, data)

/** 负责人初审异议 */
export const leaderReviewObjection = (id: number, data: any) => request.patch(`${BASE}/objections/${id}/leader_review/`, { ...data, action: 'leader_review' })

/** 老师确认异议 */
export const teacherConfirmObjection = (id: number, data: any) => request.patch(`${BASE}/objections/${id}/teacher_confirm/`, { ...data, action: 'teacher_confirm' })
