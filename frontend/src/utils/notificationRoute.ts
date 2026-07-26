import type { RouteLocationRaw } from 'vue-router'
import type { Notification } from '@/types'

function relatedObjectId(notification: Notification): number | null {
  const value = Number(notification.related_object_id ?? notification.related_id)
  return Number.isInteger(value) && value > 0 ? value : null
}

/** 将站内通知统一映射到对应业务入口。 */
export function notificationRelatedRoute(notification: Notification): RouteLocationRaw | null {
  const type = String(notification.related_object_type || notification.related_type || '')
    .trim()
    .toLowerCase()
  const category = String(notification.notification_type || notification.category || '')
    .trim()
    .toLowerCase()
  const id = relatedObjectId(notification)

  if (type === 'project' && id) return `/projects/${id}`
  if (type === 'task' && id) return { path: '/tasks', query: { task_id: String(id) } }
  if (type === 'competition' || type.startsWith('competition_')) return '/competitions'
  if (type === 'scheduled_report' || type === 'report') return '/reports'
  if (type === 'contribution') return '/contributions/pending'
  if (type === 'ranking_objection') return '/contributions'
  if (type === 'ip_return' || type === 'ip_objection') return '/intellectual-property/todo'
  if (type === 'flexible_work_schedule') return '/members/schedule'
  if (type === 'sensitive_request') return '/sensitive/pending'
  if (['finance_expense', 'finance_income', 'financebudget'].includes(type)) return '/finance'

  if (category === 'project') return '/projects'
  if (category === 'task') return '/tasks'
  if (category === 'competition') return '/competitions'
  if (category === 'report') return '/reports'
  if (category === 'contribution') return '/contributions'
  if (category === 'ip') return '/intellectual-property'
  if (category === 'sensitive') return '/sensitive'
  if (category === 'schedule') return '/members/schedule'
  if (category === 'finance') return '/finance'
  if (category === 'announcement') return '/announcements'
  return null
}
