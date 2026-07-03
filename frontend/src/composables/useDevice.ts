import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 设备类型检测 Composable
 * 根据窗口宽度判断当前设备类型（PC/移动端），监听窗口 resize 事件
 */
export function useDevice(breakpoint = 768) {
  const isMobile = ref<boolean>(typeof window !== 'undefined' ? window.innerWidth < breakpoint : false)

  /** 检测设备类型 */
  function checkDevice(): void {
    isMobile.value = window.innerWidth < breakpoint
  }

  onMounted(() => {
    checkDevice()
    window.addEventListener('resize', checkDevice)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', checkDevice)
  })

  return {
    isMobile,
  }
}
