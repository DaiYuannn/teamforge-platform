import { useUserStore } from '@/stores/user'
import type { UserRole } from '@/types'

/**
 * 权限检查 Composable
 * 基于当前用户角色判断权限
 */
export function usePermission() {
  const userStore = useUserStore()

  /** 检查用户是否拥有指定角色 */
  function hasRole(role: UserRole): boolean {
    return userStore.role === role
  }

  /** 检查用户是否拥有指定角色中的任意一个 */
  function hasAnyRole(roles: UserRole[]): boolean {
    return roles.includes(userStore.role as UserRole)
  }

  /** 检查用户是否拥有全部指定角色 */
  function hasAllRoles(roles: UserRole[]): boolean {
    return roles.every((r) => userStore.role === r)
  }

  /** 检查用户是否为管理员 */
  function isAdmin(): boolean {
    return userStore.role === 'sys_admin'
  }

  /** 检查用户是否为老师 */
  function isTeacher(): boolean {
    return userStore.role === 'teacher'
  }

  /** 检查用户是否可以管理项目（老师或管理员） */
  function canManageProject(): boolean {
    return isAdmin() || isTeacher()
  }

  return {
    hasRole,
    hasAnyRole,
    hasAllRoles,
    isAdmin,
    isTeacher,
    canManageProject,
  }
}
