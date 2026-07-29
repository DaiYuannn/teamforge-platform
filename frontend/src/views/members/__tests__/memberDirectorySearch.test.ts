import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Member, TeamRole } from '@/types'

const {
  getMembersMock,
  getTeamsMock,
  smartNavigateMock,
} = vi.hoisted(() => ({
  getMembersMock: vi.fn(),
  getTeamsMock: vi.fn(),
  smartNavigateMock: vi.fn(),
}))

vi.mock('@/api/members', () => ({
  getMembers: getMembersMock,
}))

vi.mock('@/api/teams', () => ({
  getTeams: getTeamsMock,
}))

vi.mock('@/composables/useMobileNavigate', () => ({
  useMobileNavigate: () => ({ smartNavigate: smartNavigateMock }),
}))

import MemberListView from '../MemberListView.vue'

function member(overrides: Partial<Member> = {}): Member {
  return {
    id: 8,
    name: '刘宇成',
    email: 'liuyucheng@example.com',
    phone: '13800000000',
    school: '示例理工大学',
    grade: '2024 级',
    major: '计算机科学与技术',
    team_role: 'member',
    membership_status: 'active',
    ...overrides,
  }
}

function mountView() {
  return shallowMount(MemberListView, {
    global: {
      stubs: {
        PageHeader: true,
        EmptyState: true,
        AvatarWithName: true,
        AccessiblePagination: true,
        'el-alert': true,
        'el-form': true,
        'el-form-item': true,
        'el-input': true,
        'el-select': true,
        'el-option': true,
        'el-button': true,
        'el-table': true,
        'el-table-column': true,
        'el-tag': true,
      },
    },
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  setActivePinia(createPinia())
  getMembersMock.mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
  getTeamsMock.mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
})

afterEach(() => {
  vi.useRealTimers()
})

describe('member directory fragment search', () => {
  it('debounces free-text changes and sends the fragment to the backend', async () => {
    const wrapper = mountView()
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      queryParams: { major?: string; page?: number }
    }

    vm.queryParams.major = '计算机'
    await vi.advanceTimersByTimeAsync(319)
    expect(getMembersMock).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()
    expect(getMembersMock).toHaveBeenCalledTimes(2)
    expect(getMembersMock).toHaveBeenLastCalledWith(expect.objectContaining({
      major: '计算机',
      page: 1,
    }))
    wrapper.unmount()
  })

  it('coalesces rapid search, school, grade and major input into one request', async () => {
    const wrapper = mountView()
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      queryParams: {
        search?: string
        school?: string
        grade?: string
        major?: string
      }
    }

    vm.queryParams.search = 'LYC'
    vm.queryParams.school = '理工'
    vm.queryParams.grade = '2024'
    vm.queryParams.major = '计算机'
    await vi.advanceTimersByTimeAsync(320)
    await flushPromises()

    expect(getMembersMock).toHaveBeenCalledTimes(2)
    expect(getMembersMock).toHaveBeenLastCalledWith(expect.objectContaining({
      search: 'LYC',
      school: '理工',
      grade: '2024',
      major: '计算机',
    }))
    wrapper.unmount()
  })

  it('uses backend results directly instead of applying an exact client-side major filter', async () => {
    const matchingMember = member()
    const wrapper = mountView()
    await flushPromises()
    getMembersMock.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [matchingMember],
    })
    const vm = wrapper.vm as unknown as {
      queryParams: { major?: string }
      memberList: Member[]
    }

    vm.queryParams.major = '计算机'
    await vi.advanceTimersByTimeAsync(320)
    await flushPromises()

    expect(vm.memberList).toEqual([matchingMember])
    expect(vm.memberList[0]?.major).toBe('计算机科学与技术')
    wrapper.unmount()
  })

  it('keeps identity and membership status as immediate select filters', async () => {
    const wrapper = mountView()
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      queryParams: {
        team_role?: TeamRole
        membership_status?: string
      }
      handleImmediateFilterChange: () => void
    }

    vm.queryParams.team_role = 'co_lead'
    vm.queryParams.membership_status = 'active'
    vm.handleImmediateFilterChange()
    await flushPromises()

    expect(getMembersMock).toHaveBeenLastCalledWith(expect.objectContaining({
      team_role: 'co_lead',
      membership_status: 'active',
    }))
    wrapper.unmount()
  })

  it('cancels a pending text search when all filters are reset', async () => {
    const wrapper = mountView()
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      queryParams: { search?: string }
      handleReset: () => void
    }

    vm.queryParams.search = '刘'
    vm.handleReset()
    await flushPromises()
    expect(getMembersMock).toHaveBeenCalledTimes(2)

    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()
    expect(getMembersMock).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })
})

describe('member directory search copy', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/views/members/MemberListView.vue'),
    'utf8',
  )

  it('describes every field covered by the main search and fragment matching', () => {
    expect(source).toContain('姓名、拼音、首字母、手机号、邮箱、学校或专业')
    expect(source).toContain('输入专业片段，如计算机')
    expect(source).toContain('输入学校名称片段')
    expect(source).toContain('输入年级片段，如 2024')
    expect(source).toContain('英文字母不区分大小写')
  })

  it('uses one form-submit path for Enter instead of issuing duplicate requests', () => {
    expect(source).toContain('@submit.prevent="handleSearch"')
    expect(source).not.toContain('@keyup.enter')
  })
})
