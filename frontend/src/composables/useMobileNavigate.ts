import { useRouter } from 'vue-router'
import { useDevice } from '@/composables/useDevice'

/**
 * 移动端智能跳转 Composable
 *
 * - 移动端：列表页跳转详情使用 router.push，详情页提供返回按钮（goBack）
 * - PC 端：可使用新窗口打开（openInNewWindow）
 *
 * 提供：
 *   - smartNavigate(route)：移动端 push，PC 端默认也 push（可传 openNew 强制新窗口）
 *   - goBack(fallback)：优先 router.back()，无历史时跳转 fallback（默认 /dashboard）
 *   - openInNewWindow(route)：PC 端新窗口打开
 */
export function useMobileNavigate() {
  const router = useRouter()
  const { isMobile } = useDevice()

  /** 默认回退路由 */
  const DEFAULT_FALLBACK = '/dashboard'

  /**
   * 智能跳转
   * @param route 目标路由路径
   * @param openNew 是否强制新窗口打开（仅 PC 端生效）
   */
  function smartNavigate(route: string, openNew = false): void {
    // PC 端且要求新窗口打开
    if (!isMobile.value && openNew) {
      openInNewWindow(route)
      return
    }
    // 移动端 / PC 端默认：当前页 push
    router.push(route)
  }

  /**
   * 在新窗口打开（PC 端使用）
   * @param route 目标路由路径
   */
  function openInNewWindow(route: string): void {
    const { origin } = window.location
    // 直接使用 router.resolve 解析完整路径，保证 hash/base 一致
    const resolved = router.resolve(route)
    const fullPath = resolved.fullPath
    window.open(`${origin}${fullPath}`, '_blank', 'noopener,noreferrer')
  }

  /**
   * 返回上一页
   * 优先使用 router.back()，无历史记录时跳转 fallback
   * @param fallback 无历史时的回退路由，默认 /dashboard
   */
  function goBack(fallback: string = DEFAULT_FALLBACK): void {
    // window.history.length 为 1 表示当前页是历史栈中的唯一记录，无上一页可返回
    if (window.history.length > 1) {
      router.back()
    } else {
      router.push(fallback)
    }
  }

  return {
    isMobile,
    smartNavigate,
    openInNewWindow,
    goBack,
  }
}
