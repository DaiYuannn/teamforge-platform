import type {
  IPParticipantOption,
  IPApplicationListItem,
  IPStatus,
  IPTodoItem,
  IPTodoResponse,
} from '@/types/intellectualProperty'
import type { Project, ProjectMember, User } from '@/types'

interface TodoStatusConfig {
  type: IPTodoItem['type']
  description: string
}

export function normalizeIPProjectFilter(value: unknown): number | undefined {
  const candidate = Array.isArray(value) ? value[0] : value
  const parsed = Number(candidate)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

export function resolveIPCreateProjectDeepLink(
  value: unknown,
  accessibleProjects: readonly Pick<Project, 'id'>[],
): number | null {
  const projectId = normalizeIPProjectFilter(value)
  if (!projectId) return null
  return accessibleProjects.some((project) => project.id === projectId)
    ? projectId
    : null
}

const TODO_STATUS_CONFIG: Partial<Record<IPStatus, TodoStatusConfig>> = {
  draft: { type: 'writing', description: '开始准备申请材料' },
  writing: { type: 'writing', description: '继续完善申请材料并提交负责人审核' },
  leader_review: { type: 'review', description: '完成项目负责人审核' },
  teacher_confirm: { type: 'confirm', description: '完成老师确认并提交科研处审核' },
  research_office_review: { type: 'submit', description: '跟进科研处审核结果' },
  returned: { type: 'return_fix', description: '查看退回原因并开始修改' },
  modifying: { type: 'return_fix', description: '完成退回修改并重新提交' },
  resubmitted: { type: 'submit', description: '跟进重新提交后的审核' },
  accepted: { type: 'submit', description: '跟进成果授权或登记' },
  authorized: { type: 'submit', description: '完成成果材料归档' },
  paused: { type: 'writing', description: '确认是否恢复申请流程' },
  deferred: { type: 'writing', description: '确认是否重启后续申请' },
}

export function mapIPApplicationsToTodos(response: IPTodoResponse): IPTodoItem[] {
  const applications: IPApplicationListItem[] = Array.isArray(response) ? response : response.results

  return applications.flatMap((application) => {
    const config = TODO_STATUS_CONFIG[application.status]
    if (!config) return []

    return [{
      type: config.type,
      application_id: application.id,
      title: application.title,
      description: config.description,
      deadline: null,
      created_at: application.updated_at,
    }]
  })
}

export function buildProjectParticipantOptions(
  project: Pick<Project, 'leader' | 'leader_name'>,
  members: readonly ProjectMember[],
): IPParticipantOption[] {
  const options = new Map<number, IPParticipantOption>()

  options.set(project.leader, {
    id: project.leader,
    name: project.leader_name || '项目负责人',
  })

  for (const member of members) {
    if (member.status && member.status !== 'active') continue
    const detail = member.user_detail || {}
    if (detail.is_active === false) continue
    if (['exited', 'external'].includes(detail.membership_status)) continue
    options.set(member.user, {
      id: member.user,
      name: detail.name || member.user_name,
      username: detail.username,
      email: detail.email,
      global_role: detail.global_role,
      membership_status: detail.membership_status,
      is_active: detail.is_active,
    })
  }

  return Array.from(options.values())
}

export function buildInternalParticipantOptions(
  users: readonly User[],
): IPParticipantOption[] {
  return users
    .filter((user) =>
      user.is_active
      && !['exited', 'external'].includes(user.membership_status || 'active'),
    )
    .map((user) => ({
      id: user.id,
      name: user.name,
      username: user.username,
      email: user.email,
      global_role: user.global_role,
      membership_status: user.membership_status,
      is_active: user.is_active,
    }))
}

export function buildTeacherConfirmerOptions(
  users: readonly User[],
): IPParticipantOption[] {
  return buildInternalParticipantOptions(users)
    .filter((user) => ['teacher', 'sys_admin'].includes(user.global_role || ''))
}

export type IPWorkflowActionKind = 'transition' | 'archive' | 'return'

export interface IPWorkflowAction {
  kind: IPWorkflowActionKind
  targetStatus: IPStatus
  label: string
  confirmation: string
  tone?: 'warning' | 'danger'
}

const action = (
  targetStatus: IPStatus,
  label: string,
  confirmation: string,
  tone?: IPWorkflowAction['tone'],
  kind: IPWorkflowActionKind = 'transition',
): IPWorkflowAction => ({ kind, targetStatus, label, confirmation, tone })

export const IP_STATUS_ACTIONS: Record<IPStatus, readonly IPWorkflowAction[]> = {
  draft: [
    action('writing', '开始撰写', '申请将进入材料撰写阶段。'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('terminated', '终止申请', '终止后无法继续流转，请确认申请不再继续。', 'danger'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  writing: [
    action('leader_review', '提交负责人审核', '请确认材料已经具备负责人审核条件。'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('terminated', '终止申请', '终止后无法继续流转，请确认申请不再继续。', 'danger'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  leader_review: [
    action('teacher_confirm', '提交老师确认', '负责人审核通过后，申请将进入老师确认阶段。'),
    action('writing', '退回继续撰写', '申请将退回材料撰写阶段。', 'warning'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  teacher_confirm: [
    action('research_office_review', '提交科研处审核', '老师确认后，申请将进入科研处审核阶段。'),
    action('leader_review', '退回负责人复核', '申请将退回项目负责人审核阶段。', 'warning'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  research_office_review: [
    action('accepted', '标记已受理', '请确认已经收到正式受理结果。'),
    action('returned', '登记审核退回', '请填写退回原因、责任人与修改期限。', 'warning', 'return'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  returned: [
    action('modifying', '开始修改', '申请将进入材料修改阶段。'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('terminated', '终止申请', '终止后无法继续流转，请确认申请不再继续。', 'danger'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  modifying: [
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('terminated', '终止申请', '终止后无法继续流转，请确认申请不再继续。', 'danger'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  resubmitted: [
    action('research_office_review', '提交复核', '申请将再次进入科研处审核阶段。'),
    action('accepted', '标记已受理', '请确认已经收到正式受理结果。'),
    action('returned', '再次退回', '请填写本次退回原因、责任人与修改期限。', 'warning', 'return'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  accepted: [
    action('authorized', '标记已授权', '请确认成果已经正式授权或登记。'),
    action('paused', '暂停申请', '暂停后可在后续恢复申请。', 'warning'),
  ],
  authorized: [
    action('archived', '归档成果', '归档前请确认最终证书和成果材料已经完整留存。', undefined, 'archive'),
  ],
  archived: [],
  paused: [
    action('draft', '恢复到准备中', '申请将恢复到准备阶段。'),
    action('writing', '恢复到撰写中', '申请将恢复到材料撰写阶段。'),
    action('leader_review', '恢复到负责人审核', '申请将恢复到负责人审核阶段。'),
    action('teacher_confirm', '恢复到老师确认', '申请将恢复到老师确认阶段。'),
    action('research_office_review', '恢复到科研处审核', '申请将恢复到科研处审核阶段。'),
    action('modifying', '恢复到修改中', '申请将恢复到材料修改阶段。'),
    action('deferred', '转为后续申请', '当前申请将转入后续申请池，可在条件成熟后重启。', 'warning'),
  ],
  terminated: [],
  deferred: [
    action('draft', '重启申请', '申请将回到准备阶段并重新启动。'),
  ],
}

export function getIPWorkflowActions(status: IPStatus): readonly IPWorkflowAction[] {
  return IP_STATUS_ACTIONS[status]
}

export function getAvailableIPWorkflowActions(
  status: IPStatus,
  canTransition: boolean,
  isPrivileged: boolean,
): readonly IPWorkflowAction[] {
  return getIPWorkflowActions(status).filter((workflowAction) => {
    if (workflowAction.kind === 'archive') return isPrivileged
    if (workflowAction.kind === 'return') return isPrivileged
    if (
      status === 'resubmitted' &&
      ['accepted', 'returned'].includes(workflowAction.targetStatus)
    ) {
      return isPrivileged
    }
    return canTransition
  })
}
