import request from './request'

// ============================================
// 数据导出 API
// ============================================

/**
 * 导出数据
 * @param type 导出类型（projects/finance/intellectual_property/contributions 等）
 * @param format 导出格式（xlsx/pdf/word）
 * @param projectId 项目ID（可选）
 * @param ipId 知识产权ID（可选）
 */
export const exportData = (type: string, format: string = 'xlsx', projectId?: number, ipId?: number) => {
  return request.get('/exports/', {
    params: { type, file_format: format, project_id: projectId, ip_id: ipId },
    responseType: 'blob',
  })
}

/**
 * 导出项目完整报告（Word 格式）
 * 专用接口，返回包含项目基本信息、阶段历程、比赛记录、经费统计、成员列表、知识产权、贡献汇总的完整报告
 * @param projectId 项目ID
 */
export const exportProjectReport = (projectId: number) => {
  return request.get(`/exports/project-report/${projectId}/`, { responseType: 'blob' })
}
