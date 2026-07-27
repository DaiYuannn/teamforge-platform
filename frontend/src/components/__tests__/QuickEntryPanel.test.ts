import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuickEntryPanel from '@/components/QuickEntryPanel.vue'
import { useUserStore } from '@/stores/user'
import type { User, UserPreferences } from '@/types'

function preferences(favoriteRoutes: string[]): UserPreferences {
  return {
    primary_color: '#176b73',
    theme_mode: 'light',
    schedule_start: '19:00',
    schedule_end: '07:00',
    default_landing: 'dashboard',
    sidebar_collapsed: false,
    notification_sound: true,
    items_per_page: 20,
    favorite_routes: favoriteRoutes,
    dashboard_layout: {},
  }
}

function currentUser(favoriteRoutes: string[]): User {
  return {
    id: 7,
    username: 'member7',
    email: 'member7@example.com',
    name: '测试成员',
    global_role: 'member',
    membership_status: 'active',
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    preferences: preferences(favoriteRoutes),
  }
}

async function mountPanel(favoriteRoutes: string[]) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = currentUser(favoriteRoutes)
  store.role = 'member'
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(QuickEntryPanel, {
    global: {
      plugins: [pinia, router, ElementPlus],
      stubs: { teleport: true },
    },
  })
  return { wrapper, store }
}

describe('QuickEntryPanel', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('renders quick entries in the current account preference order', async () => {
    const { wrapper } = await mountPanel(['/tasks', '/projects', '/todo'])

    expect(wrapper.findAll('.quick-entry-copy strong').map((node) => node.text()))
      .toEqual(['任务管理', '项目管理', '待办事项'])
    wrapper.unmount()
  })

  it('saves the reordered favorite routes to the current account', async () => {
    const { wrapper, store } = await mountPanel(['/tasks', '/projects'])
    const savePreference = vi.spyOn(store, 'savePreference')
      .mockResolvedValue({
        ...preferences(['/projects', '/tasks']),
        primary_color: '#176b73',
      })

    await wrapper.find('.quick-entry-header button').trigger('click')
    await flushPromises()
    await wrapper.get('[aria-label="下移任务管理"]').trigger('click')
    const saveButton = wrapper.findAll('button')
      .find((button) => button.text().includes('保存到当前账户'))
    expect(saveButton).toBeTruthy()
    await saveButton!.trigger('click')
    await flushPromises()

    expect(savePreference).toHaveBeenCalledWith({
      favorite_routes: ['/projects', '/tasks'],
    })
    wrapper.unmount()
  })
})
