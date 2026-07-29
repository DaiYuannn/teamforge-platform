import type {
  ApprovalFlow,
  ApprovalRequest,
  TeamMembershipAction,
  TeamMembershipApprovalMetadata,
} from '@/api/platform'

export function canReviewApprovalRequest(
  request: ApprovalRequest,
  flows: ApprovalFlow[],
  user: { id?: number; role?: string; isManager?: boolean },
): boolean {
  if (request.status !== 'pending' || request.applicant === user.id) return false
  if (typeof request.can_review === 'boolean') return request.can_review

  const step = flows.find((flow) => flow.id === request.flow)?.steps[request.current_step]
  if (!step) return false

  const reviewerRoles = new Set([
    ...(step.reviewer_roles || []),
    ...(step.reviewer_role ? [step.reviewer_role] : []),
  ])
  return (
    reviewerRoles.has(user.role || '')
    || Boolean(step.reviewer_ids?.includes(user.id || -1))
  )
}

export function canCancelApprovalRequest(request: ApprovalRequest, userId?: number): boolean {
  return request.status === 'pending' && request.applicant === userId
}

export function approvalRequestIdFromQuery(
  value: unknown,
): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const requestId = Number(raw)
  return Number.isInteger(requestId) && requestId > 0 ? requestId : null
}

export function buildTeamMembershipMetadata(input: {
  action: TeamMembershipAction
  targetTeamId: number | null
  membershipId: number | null
  requestedRole: string
  reason: string
}): TeamMembershipApprovalMetadata | null {
  if (
    !input.targetTeamId
    || !input.requestedRole
    || !input.reason.trim()
    || (input.action !== 'join' && !input.membershipId)
  ) return null

  return {
    action: input.action,
    target_team_id: input.targetTeamId,
    requested_role: input.requestedRole,
    reason: input.reason.trim(),
    ...(input.membershipId
      ? { membership_id: input.membershipId }
      : {}),
  }
}
