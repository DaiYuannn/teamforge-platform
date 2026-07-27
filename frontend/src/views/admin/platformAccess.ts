import type { ApprovalFlow, ApprovalRequest } from '@/api/platform'

export function canReviewApprovalRequest(
  request: ApprovalRequest,
  flows: ApprovalFlow[],
  user: { id?: number; role?: string; isManager: boolean },
): boolean {
  if (request.status !== 'pending' || request.applicant === user.id) return false

  const step = flows.find((flow) => flow.id === request.flow)?.steps[request.current_step]
  if (!step) return user.isManager

  const hasExplicitReviewer = Boolean(step.reviewer_role || step.reviewer_ids?.length)
  if (!hasExplicitReviewer) return user.isManager
  return step.reviewer_role === user.role || Boolean(step.reviewer_ids?.includes(user.id || -1))
}

export function canCancelApprovalRequest(request: ApprovalRequest, userId?: number): boolean {
  return request.status === 'pending' && request.applicant === userId
}
