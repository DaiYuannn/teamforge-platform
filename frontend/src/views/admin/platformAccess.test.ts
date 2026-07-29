import { describe, expect, it } from 'vitest'
import type { ApprovalFlow, ApprovalRequest, ApprovalStep } from '@/api/platform'
import {
  approvalRequestIdFromQuery,
  buildTeamMembershipMetadata,
  canCancelApprovalRequest,
  canReviewApprovalRequest,
} from './platformAccess'

const request = (overrides: Partial<ApprovalRequest> = {}): ApprovalRequest => ({
  id: 1,
  applicant: 5,
  applicant_name: '申请人',
  flow: 2,
  flow_name: '项目审批',
  flow_type: 'project',
  status: 'pending',
  status_display: '待审批',
  title: '材料申请',
  content: '',
  current_step: 0,
  current_step_name: '负责人审批',
  reviewer_ids: [],
  reviewer_roles: [],
  reviewer_names: [],
  can_review: false,
  review_history: [],
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
  it('uses the server-computed current reviewer decision', () => {
    expect(canReviewApprovalRequest(request({ can_review: true }), [flow({ reviewer_role: 'team_manager' })], {
      id: 8,
      role: 'member',
    })).toBe(true)
    expect(canReviewApprovalRequest(request({ can_review: false }), [flow({ reviewer_ids: [8] })], {
      id: 8,
      role: 'teacher',
      isManager: true,
    })).toBe(false)
  })

  it('prevents applicants from reviewing and only lets them cancel pending requests', () => {
    expect(canReviewApprovalRequest(request({ can_review: true }), [flow({ reviewer_role: 'member' })], {
      id: 5,
      role: 'member',
      isManager: false,
    })).toBe(false)
    expect(canCancelApprovalRequest(request(), 5)).toBe(true)
    expect(canCancelApprovalRequest(request({ status: 'approved' }), 5)).toBe(false)
  })

  it('does not grant a client-side manager fallback for unassigned legacy nodes', () => {
    expect(canReviewApprovalRequest(request({
      can_review: undefined as unknown as boolean,
    }), [flow({ name: '负责人审批' })], {
      id: 8,
      role: 'teacher',
      isManager: true,
    })).toBe(false)
  })

  it('keeps explicit-id fallback for an older server response', () => {
    expect(canReviewApprovalRequest(request({
      can_review: undefined as unknown as boolean,
    }), [flow({ reviewer_ids: [8] })], {
      id: 8,
      role: 'member',
    })).toBe(true)
  })

  it('builds the structured team transfer metadata expected by the API', () => {
    expect(buildTeamMembershipMetadata({
      action: 'transfer',
      targetTeamId: 12,
      membershipId: 33,
      requestedRole: 'member',
      reason: '  转入比赛项目组  ',
    })).toEqual({
      action: 'transfer',
      target_team_id: 12,
      membership_id: 33,
      requested_role: 'member',
      reason: '转入比赛项目组',
    })
    expect(buildTeamMembershipMetadata({
      action: 'role_change',
      targetTeamId: 12,
      membershipId: null,
      requestedRole: 'co_lead',
      reason: '提权',
    })).toBeNull()
  })

  it('parses a workflow todo request id for automatic positioning', () => {
    expect(approvalRequestIdFromQuery('42')).toBe(42)
    expect(approvalRequestIdFromQuery(['7'])).toBe(7)
    expect(approvalRequestIdFromQuery('invalid')).toBeNull()
  })
})
