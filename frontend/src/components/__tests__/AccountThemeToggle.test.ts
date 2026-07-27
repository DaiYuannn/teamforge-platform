import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { savePreference, successMessage, errorMessage } = vi.hoisted(() => ({
  savePreference: vi.fn(),
  successMessage: vi.fn(),
  errorMessage: vi.fn(),
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ savePreference }),
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: successMessage,
    error: errorMessage,
  },
}))

import AccountThemeToggle from '@/components/AccountThemeToggle.vue'

const TooltipStub = defineComponent({
  template: '<div><slot /></div>',
})
const ButtonStub = defineComponent({
  inheritAttrs: false,
  props: { disabled: Boolean },
  emits: ['click'],
  template: '<button v-bind="$attrs" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
})
const IconStub = defineComponent({
  template: '<span><slot /></span>',
})

function mountToggle() {
  return mount(AccountThemeToggle, {
    global: {
      stubs: {
        'el-tooltip': TooltipStub,
        'el-button': ButtonStub,
        'el-icon': IconStub,
      },
    },
  })
}

describe('AccountThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.dataset.theme = 'light'
    document.documentElement.dataset.themeMode = 'system'
  })

  it('saves the opposite explicit account mode and follows the resolved document theme', async () => {
    savePreference.mockImplementation(async ({ theme_mode }: { theme_mode: 'light' | 'dark' }) => {
      document.documentElement.dataset.theme = theme_mode
    })
    const wrapper = mountToggle()

    expect(wrapper.get('button').attributes('aria-label')).toBe('切换为夜间模式')
    await wrapper.get('button').trigger('click')
    await nextTick()

    expect(savePreference).toHaveBeenCalledWith({ theme_mode: 'dark' })
    expect(successMessage).toHaveBeenCalledWith('已切换为夜间模式')
    expect(wrapper.get('button').attributes('aria-label')).toBe('切换为日间模式')
  })

  it('overrides a scheduled mode only after an explicit click', async () => {
    document.documentElement.dataset.theme = 'dark'
    document.documentElement.dataset.themeMode = 'schedule'
    savePreference.mockResolvedValue({})
    const wrapper = mountToggle()

    await wrapper.get('button').trigger('click')

    expect(savePreference).toHaveBeenCalledWith({ theme_mode: 'light' })
    expect(document.documentElement.dataset.themeMode).toBe('schedule')
  })

  it('reports a failed account save while the store owns rollback', async () => {
    savePreference.mockRejectedValue(new Error('save failed'))
    const wrapper = mountToggle()

    await wrapper.get('button').trigger('click')

    expect(errorMessage).toHaveBeenCalledWith('界面模式保存失败，已恢复原设置')
    expect(wrapper.get('button').attributes('aria-label')).toBe('切换为夜间模式')
  })
})
