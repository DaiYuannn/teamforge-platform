import type { Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'
import type { UserRole } from '@/types'

/**
 * v-permission 指令
 * 根据用户角色控制元素显隐
 *
 * 用法:
 *   v-permission="'sys_admin'"            // 仅管理员可见
 *   v-permission="['sys_admin','teacher']" // 管理员或老师可见
 */
export const permissionDirective: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const userStore = useUserStore()
    const value = binding.value as UserRole | UserRole[]

    if (!value) return

    const allowedRoles = Array.isArray(value) ? value : [value]
    const currentRole = userStore.role as UserRole

    // 当前用户角色不在允许列表中，则移除元素
    if (!allowedRoles.includes(currentRole)) {
      el.parentNode?.removeChild(el)
    }
  },
}
