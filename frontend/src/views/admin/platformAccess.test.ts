import { describe, expect, it } from 'vitest'
import type { ApprovalFlow, ApprovalRequest, ApprovalStep } from '@/api/platform'
import { canCancelApprovalRequest, canReviewApprovalRequest } from './platformAccess'

const request = (overrides: Partial<ApprovalRequest> = {}): ApprovalRequest => ({
  id: 1,
  applicant: 5,
  applicant_name: '申请人',
  flow: 2,
  flow_name: '项目审批',
  status: 'pending',
  status_display: '待审批',
  title: '材料申请',
  content: '',
  current_step: 0,
  metadata: {},
  created_at: '2026-07-26T10:00:00+08:00',
  updated_at: '2026-07-26T10:00:00+08:00',
  ...overrides,
})

const flow = (step: Partial<ApprovalStep>): ApprovalFlow => ({
  id: 2,
  name: '项目审批',
  flow_type: 'project',
  steps: [{ name: '负责人审批', ...step }],
  is_active: true,
  created_at: '2026-07-26T10:00:00+08:00',
})

describe('platform approval access', () => {
  it('only enables an explicitly matched current reviewer', () => {
    expect(canReviewApprovalRequest(request(), [flow({ reviewer_role: 'teacher' })], {
      id: 8,
      role: 'teacher',
      isManager: true,
    })).toBe(true)
    expect(canReviewApprovalRequest(request(), [flow({ reviewer_ids: [9] })], {
      id: 8,
      role: 'teacher',
      isManager: true,
    })).toBe(false)
  })

  it('prevents applicants from reviewing and only lets them cancel pending requests', () => {
    expect(canReviewApprovalRequest(request(), [flow({ reviewer_role: 'member' })], {
      id: 5,
      role: 'member',
      isManager: false,
    })).toBe(false)
    expect(canCancelApprovalRequest(request(), 5)).toBe(true)
    expect(canCancelApprovalRequest(request({ status: 'approved' }), 5)).toBe(false)
  })

  it('allows managers to process legacy flows without reviewer metadata', () => {
    expect(canReviewApprovalRequest(request(), [flow({ name: '负责人审批' })], {
      id: 8,
      role: 'teacher',
      isManager: true,
    })).toBe(true)
  })
})
