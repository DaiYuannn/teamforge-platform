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
