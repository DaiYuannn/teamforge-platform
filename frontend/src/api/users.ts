import { get, post, patch, del } from './request'
import type { User, UserFormData, PaginatedResponse, PaginationParams } from '@/types'

/** 用户查询参数 */
export interface UserQueryParams extends PaginationParams {
  global_role?: string
  is_active?: boolean
}

/** 获取用户列表 */
export function getUsers(params: UserQueryParams): Promise<PaginatedResponse<User>> {
  return get<PaginatedResponse<User>>('/users/', params)
}

/** 创建用户 */
export function createUser(data: UserFormData): Promise<User> {
  return post<User>('/users/', data)
}

/** 更新用户 */
export function updateUser(id: number, data: Partial<UserFormData>): Promise<User> {
  return patch<User>(`/users/${id}/`, data)
}

/** 删除用户 */
export function deleteUser(id: number): Promise<void> {
  return del<void>(`/users/${id}/`)
}

/** 获取用户详情 */
export function getUser(id: number): Promise<User> {
  return get<User>(`/users/${id}/`)
}
