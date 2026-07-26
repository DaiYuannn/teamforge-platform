import { get, post, del, upload, download } from './request'
import type {
  FileAsset,
  FileVersion,
  FileUploadParams,
  FileQueryParams,
  PaginatedResponse,
} from '@/types'

export type { FileQueryParams }

/** 获取文件列表 */
export function getFiles(params: FileQueryParams): Promise<PaginatedResponse<FileAsset>> {
  return get<PaginatedResponse<FileAsset>>('/files/', params)
}

/** 按项目获取文件列表 */
export function getFilesByProject(projectId: number): Promise<FileAsset[]> {
  return get<PaginatedResponse<FileAsset> | FileAsset[]>('/files/', {
    project: projectId,
    page: 1,
    page_size: 100,
  }).then((response) => (Array.isArray(response) ? response : response.results))
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

export function getFileVersions(id: number): Promise<FileVersion[]> {
  return get<FileVersion[]>(`/files/${id}/versions/`)
}

export function uploadFileVersion(id: number, file: File): Promise<FileAsset> {
  const formData = new FormData()
  formData.append('file', file)
  return upload<FileAsset>(`/files/${id}/upload-version/`, formData)
}

export function downloadFileVersion(id: number, versionId: number): Promise<Blob> {
  return download(`/files/${id}/versions/${versionId}/download/`)
}

export function restoreFileVersion(id: number, versionId: number): Promise<FileAsset> {
  return post<FileAsset>(`/files/${id}/versions/${versionId}/restore/`)
}
