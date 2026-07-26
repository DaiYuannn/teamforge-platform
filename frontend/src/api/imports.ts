import { download, get, post, upload } from './request'
import type {
  ImportModule,
  FieldMapping,
  ImportPreviewResult,
  ImportTask,
  PaginatedResponse,
} from '@/types'

/** 预览导入数据（上传文件并返回字段映射建议和预览行） */
export function previewImport(
  file: File,
  module: ImportModule,
  fieldMapping?: FieldMapping
): Promise<ImportPreviewResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('module', module)
  if (fieldMapping) {
    formData.append('field_mapping', JSON.stringify(fieldMapping))
  }
  return upload<ImportPreviewResult>('/imports/tasks/preview/', formData)
}

/** 确认导入（执行实际数据导入） */
export function confirmImport(
  taskId: number,
  fieldMapping?: FieldMapping
): Promise<{ created_count: number; error_count: number; errors?: Record<string, unknown> }> {
  const data = fieldMapping ? { field_mapping: fieldMapping } : undefined
  return post(`/imports/tasks/${taskId}/confirm/`, data)
}

/** 回滚导入（撤销已导入的数据） */
export function rollbackImport(taskId: number): Promise<void> {
  return post<void>(`/imports/tasks/${taskId}/rollback/`)
}

/** 获取导入任务列表 */
export function getImportTasks(): Promise<PaginatedResponse<ImportTask>> {
  return get<PaginatedResponse<ImportTask>>('/imports/tasks/')
}

/** 下载与当前导入模块匹配的空白模板。 */
export function downloadImportTemplate(module: ImportModule): Promise<Blob> {
  return download('/exports/template/', { params: { type: module } })
}
