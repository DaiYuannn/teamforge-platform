import { get, post, patch, del, upload, download } from './request'
import type {
  FileAsset,
  FileVersion,
  FileUploadParams,
  FileQueryParams,
  PaginatedResponse,
} from '@/types'

export type { FileQueryParams }

export interface FileTag {
  id: number
  name: string
  color: string
  project?: number | null
  project_name?: string
  created_by?: number
  created_by_name?: string
  created_at: string
}

export interface FileTagSummary {
  id: number
  name: string
  color: string
}

export interface FileTagRelation {
  id: number
  file: number
  tag: number
  tag_name: string
  tag_color: string
}

export interface ManagedFileAsset extends FileAsset {
  folder?: number | null
  folder_name?: string
  tags?: FileTagSummary[]
  deleted_at?: string | null
  deleted_by_name?: string
}

export interface FileFolder {
  id: number
  project: number
  project_name?: string
  name: string
  parent?: number | null
  parent_name?: string
  path: string
  file_count: number
  created_by?: number
  created_by_name?: string
  created_at: string
  updated_at: string
}

export interface FileShareLink {
  id: number
  file: number
  file_name: string
  created_by: number
  created_by_name?: string
  token: string
  expire_at?: string | null
  max_views?: number | null
  view_count: number
  is_active: boolean
  is_expired: boolean
  is_valid: boolean
  created_at: string
}

export interface OfficePreviewSection {
  title: string
  paragraphs: string[]
  tables: string[][][]
}

export interface OfficePreview {
  type: 'docx' | 'xlsx' | 'pptx'
  name: string
  sections: OfficePreviewSection[]
  truncated: boolean
  limits: {
    source_bytes: number
    text_chars: number
    rows_per_table: number
    columns_per_table: number
  }
}

export interface FileManagementQueryParams extends FileQueryParams {
  folder?: number | 'root'
  tag?: number
}

async function getAllPages<T>(
  url: string,
  params: Record<string, unknown>,
  pageSize: number,
): Promise<T[]> {
  const results: T[] = []
  let page = 1
  while (true) {
    const response = await get<PaginatedResponse<T> | T[]>(url, {
      ...params,
      page,
      page_size: pageSize,
    })
    if (Array.isArray(response)) return [...results, ...response]
    results.push(...response.results)
    if (!response.next) return results
    page += 1
  }
}

/** 获取文件列表 */
export function getFiles(params: FileManagementQueryParams): Promise<PaginatedResponse<ManagedFileAsset>> {
  return get<PaginatedResponse<ManagedFileAsset>>('/files/', params)
}

/** 获取单个文件详情。 */
export function getFile(id: number): Promise<ManagedFileAsset> {
  return get<ManagedFileAsset>(`/files/${id}/`)
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
export function uploadFile(
  projectId: number,
  file: File,
  data: FileUploadParams & { folder?: number | null },
): Promise<ManagedFileAsset> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('project', String(projectId))
  formData.append('level', data.level)
  formData.append('name', file.name)
  if (data.folder != null) {
    formData.append('folder', String(data.folder))
  }
  if (data.description) {
    formData.append('description', data.description)
  }
  return upload<ManagedFileAsset>('/files/', formData)
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

export function getFileFolders(projectId: number): Promise<FileFolder[]> {
  return getAllPages<FileFolder>('/files/folders/', { project: projectId }, 200)
}

export function createFileFolder(data: {
  project: number
  name: string
  parent?: number | null
}): Promise<FileFolder> {
  return post<FileFolder>('/files/folders/', data)
}

export function updateFileFolder(
  id: number,
  data: { name?: string; parent?: number | null },
): Promise<FileFolder> {
  return patch<FileFolder>(`/files/folders/${id}/`, data)
}

export function deleteFileFolder(id: number): Promise<void> {
  return del<void>(`/files/folders/${id}/`)
}

export function moveFile(id: number, folder: number | null): Promise<ManagedFileAsset> {
  return post<ManagedFileAsset>(`/files/${id}/move/`, { folder })
}

export function getFileTags(projectId?: number): Promise<FileTag[]> {
  return getAllPages<FileTag>(
    '/files/tags/',
    projectId ? { project: projectId } : {},
    200,
  )
}

export function createFileTag(data: {
  name: string
  color: string
  project?: number | null
}): Promise<FileTag> {
  return post<FileTag>('/files/tags/', data)
}

export function updateFileTag(
  id: number,
  data: { name?: string; color?: string },
): Promise<FileTag> {
  return patch<FileTag>(`/files/tags/${id}/`, data)
}

export function deleteFileTag(id: number): Promise<void> {
  return del<void>(`/files/tags/${id}/`)
}

export function getFileTagRelations(fileId: number): Promise<FileTagRelation[]> {
  return get<FileTagRelation[]>('/files/tags/by-file/', { file: fileId })
}

export function replaceFileTags(fileId: number, currentIds: number[], nextIds: number[]): Promise<unknown[]> {
  const current = new Set(currentIds)
  const next = new Set(nextIds)
  const assign = nextIds.filter((id) => !current.has(id))
  const unassign = currentIds.filter((id) => !next.has(id))
  const requests: Promise<unknown>[] = []
  if (assign.length) {
    requests.push(post('/files/tags/assign/', { file: fileId, tags: assign }))
  }
  if (unassign.length) {
    requests.push(post('/files/tags/unassign/', { file: fileId, tags: unassign }))
  }
  return Promise.all(requests)
}

export function getFileShareLinks(fileId: number): Promise<FileShareLink[]> {
  return getAllPages<FileShareLink>('/files/shares/', { file: fileId }, 100)
}

export function createFileShareLink(data: {
  file: number
  expire_at?: string | null
  max_views?: number | null
}): Promise<FileShareLink> {
  return post<FileShareLink>('/files/shares/', data)
}

export function revokeFileShareLink(id: number): Promise<FileShareLink> {
  return post<FileShareLink>(`/files/shares/${id}/revoke/`)
}

export function buildFileShareUrl(token: string): string {
  const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const relative = `${apiBase.replace(/\/$/, '')}/files/shares/download/?token=${encodeURIComponent(token)}`
  return new URL(relative, window.location.origin).toString()
}

export function getRecycledFiles(): Promise<ManagedFileAsset[]> {
  return get<ManagedFileAsset[]>('/recycle-bin/', { type: 'file' })
}

export function restoreRecycledFile(id: number): Promise<void> {
  return post<void>('/recycle-bin/', { type: 'file', id })
}

export function permanentlyDeleteFile(id: number): Promise<void> {
  return del<void>('/recycle-bin/', { params: { type: 'file', id } })
}

export function getOfficePreview(id: number): Promise<OfficePreview> {
  return get<OfficePreview>(`/files/${id}/office-preview/`)
}
