import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))

vi.mock('@/api/request', () => mocks)

import {
  approveApprovalRequest,
  createCustomForm,
  createGitRepository,
  createRoleAssignment,
  getCustomRoles,
  getExternalPlatforms,
} from '@/api/platform'

beforeEach(() => Object.values(mocks).forEach((mock) => mock.mockReset()))

describe('platform capability API contract', () => {
  it('uses the custom-role and assignment resources', async () => {
    await getCustomRoles({ search: '项目' })
    await createRoleAssignment({ user: 7, role: 3, project: null })

    expect(mocks.get).toHaveBeenCalledWith('/users/roles/', {
      page: 1,
      page_size: 100,
      search: '项目',
    })
    expect(mocks.post).toHaveBeenCalledWith('/users/role-assignments/', {
      user: 7,
      role: 3,
      project: null,
    })
  })

  it('sends structured approval, form, and integration payloads', async () => {
    await approveApprovalRequest(11, '资料完整')
    await createCustomForm({
      name: '材料收集',
      fields: [{ key: 'link', label: '材料链接', type: 'text', required: true }],
      is_active: true,
    })
    await getExternalPlatforms({ is_active: true })
    await createGitRepository({
      url: 'https://example.com/team/repo.git',
      branch: 'main',
      project: 9,
      is_active: true,
    })

    expect(mocks.post).toHaveBeenCalledWith('/approvals/requests/11/approve/', {
      opinion: '资料完整',
    })
    expect(mocks.post).toHaveBeenCalledWith('/common/forms/', expect.objectContaining({
      name: '材料收集',
      is_active: true,
    }))
    expect(mocks.get).toHaveBeenCalledWith('/integrations/external-platforms/', {
      page: 1,
      page_size: 100,
      is_active: true,
    })
    expect(mocks.post).toHaveBeenCalledWith('/integrations/git-repositories/', expect.objectContaining({
      project: 9,
      branch: 'main',
    }))
  })
})
