import { get, post, del, upload, download } from './request'
import type { FileAsset, FileUploadParams, FileQueryParams, PaginatedResponse } from '@/types'

export type { FileQueryParams }

/** 获取文件列表 */
export function getFiles(params: FileQueryParams): Promise<PaginatedResponse<FileAsset>> {
  return get<PaginatedResponse<FileAsset>>('/files/', params)
}

/** 按项目获取文件列表 */
export function getFilesByProject(projectId: number): Promise<FileAsset[]> {
  return get<FileAsset[]>('/files/', { project: projectId, page_size: 999 })
}

/** 上传文件（支持三级权限选择） */
export function uploadFile(projectId: number, file: File, data: FileUploadParams): Promise<FileAsset> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('project', String(projectId))
  formData.append('level', data.level)
  if (data.description) {
    formData.append('description', data.description)
  }
  return upload<FileAsset>('/files/', formData)
}

/** 下载文件 */
export function downloadFile(id: number): Promise<Blob> {
  return download(`/files/${id}/download/`)
}

/** 删除文件 */
export function deleteFile(id: number): Promise<void> {
  return del<void>(`/files/${id}/`)
}
