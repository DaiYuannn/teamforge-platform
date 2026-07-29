import dayjs from 'dayjs'
import type {
  FinanceFundTodosResponse,
  FinanceTraceabilitySummaryResponse,
} from '@/api/finance'
import type {
  FinanceLedgerAllocation,
  FinanceLedgerAttachment,
  FinanceLedgerExpense,
  FinanceLedgerIncome,
  FinanceLedgerPayment,
  FinanceLedgerStatus,
  FinanceMetricSummary,
  FinancePerspective,
  FinanceTodoCounts,
  FinanceTraceabilityGroup,
  FinanceTraceabilityLeaf,
} from '@/types/financeLedger'

export interface FinanceAllocationEntryRef {
  id: number
  project: number
  event?: number | null
}

export interface FinanceTraceEntryMetadata {
  leader_names: string[]
  participant_names: string[]
  award_result: string
}

/**
 * Index the authoritative participant and award data returned by the
 * traceability endpoint. The general competition picker is paginated and may
 * not contain every historical entry.
 */
export function buildTraceEntryMetadataIndex(
  response?: FinanceTraceabilitySummaryResponse | null,
): Map<number, FinanceTraceEntryMetadata> {
  const index = new Map<number, FinanceTraceEntryMetadata>()
  for (const group of response?.groups || []) {
    for (const entry of group.entries || []) {
      const participants = (entry.participants || []).filter((item) => item.name)
      const uniqueNames = (names: string[]) => names.filter(
        (name, position, list) => list.indexOf(name) === position,
      )
      index.set(entry.competition_entry, {
        leader_names: uniqueNames(
          participants
            .filter((item) => item.role === 'leader')
            .map((item) => item.name),
        ),
        participant_names: uniqueNames(participants.map((item) => item.name)),
        award_result: entry.is_awarded
          ? entry.award_level || '已获奖'
          : entry.competition_status === 'completed'
            ? '未获奖'
            : '结果待公布',
      })
    }
  }
  return index
}

/**
 * Resolve the competition edition that constrains an allocation editor.
 *
 * An explicit anchor wins. Otherwise the first selected entry with a concrete
 * CompetitionEvent locks the editor, which lets the UI start from either the
 * edition selector or the first allocation row.
 */
export function resolveAllocationEventId(
  anchorEventId: number | undefined,
  selectedEntryIds: Array<number | undefined>,
  entries: FinanceAllocationEntryRef[],
): number | undefined {
  if (anchorEventId) return anchorEventId
  for (const entryId of selectedEntryIds) {
    if (!entryId) continue
    const eventId = entries.find((entry) => entry.id === entryId)?.event
    if (eventId) return eventId
  }
  return undefined
}

/** Return every project entry in the locked edition, or all entries before lock. */
export function allocationEntriesForEvent<T extends FinanceAllocationEntryRef>(
  entries: T[],
  eventId?: number,
): T[] {
  if (!eventId) return entries
  return entries.filter((entry) => entry.event === eventId)
}

/** Guard the submit path even when form state is changed outside the selector. */
export function allocationTargetsShareEvent(
  selectedEntryIds: Array<number | undefined>,
  entries: FinanceAllocationEntryRef[],
  anchorEventId?: number,
): boolean {
  const selectedIds = selectedEntryIds.filter((entryId): entryId is number => Boolean(entryId))
  if (!selectedIds.length) return true
  const selectedEntries = selectedIds
    .map((entryId) => entries.find((entry) => entry.id === entryId))
    .filter((entry): entry is FinanceAllocationEntryRef => Boolean(entry))
  if (selectedEntries.length !== selectedIds.length) return false
  const eventId = resolveAllocationEventId(anchorEventId, selectedIds, entries)
  return Boolean(eventId) && selectedEntries.every((entry) => entry.event === eventId)
}

/** Preserve the legacy allocation mode: every target stays in the anchor project. */
export function allocationTargetsBelongToProject(
  selectedEntryIds: Array<number | undefined>,
  entries: FinanceAllocationEntryRef[],
  projectId?: number,
): boolean {
  const selectedIds = selectedEntryIds.filter((entryId): entryId is number => Boolean(entryId))
  if (!selectedIds.length) return true
  if (!projectId) return false
  const selectedEntries = selectedIds
    .map((entryId) => entries.find((entry) => entry.id === entryId))
    .filter((entry): entry is FinanceAllocationEntryRef => Boolean(entry))
  return selectedEntries.length === selectedIds.length
    && selectedEntries.every((entry) => entry.project === projectId)
}

/**
 * Filter an allocated ledger by destination rather than by its anchor project.
 * The returned clone carries only matching allocation shares so traceability
 * grouping cannot leak unrelated projects or editions into a filtered view.
 */
export function filterLedgerRecordByDestination<
  T extends FinanceLedgerExpense | FinanceLedgerIncome,
>(
  item: T,
  projectId?: number,
  eventId?: number,
): T | null {
  if (item.allocations?.length) {
    if (!projectId && !eventId) return item
    const allocations = item.allocations.filter((allocation) => (
      (!projectId || (allocation.project ?? item.project) === projectId)
      && (!eventId || (allocation.event ?? item.event) === eventId)
    ))
    return allocations.length ? { ...item, allocations } : null
  }
  if (projectId && item.project !== projectId) return null
  if (eventId && item.event !== eventId) return null
  return item
}

export function moneyNumber(value: number | string | null | undefined): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/** Amount attributed to the currently retained allocation slice. */
export function attributedRecordAmount(
  item: FinanceLedgerExpense | FinanceLedgerIncome,
): number {
  if (!item.allocations?.length) return moneyNumber(item.amount)
  return item.allocations.reduce(
    (sum, allocation) => sum + moneyNumber(allocation.amount),
    0,
  )
}

/** Completed payment attributed proportionally to the retained split. */
export function attributedCompletedPaymentAmount(
  expense: FinanceLedgerExpense,
): number {
  const total = moneyNumber(expense.amount)
  if (total <= 0) return 0
  return completedPaymentAmount(expense) * attributedRecordAmount(expense) / total
}

/** Outstanding amount attributed to the retained split. */
export function attributedRemainingPayable(
  expense: FinanceLedgerExpense,
): number {
  return Math.max(
    0,
    attributedRecordAmount(expense) - attributedCompletedPaymentAmount(expense),
  )
}

export function normalizedExpenseStatus(expense: FinanceLedgerExpense): FinanceLedgerStatus {
  const status = expense.reimbursement_status || 'draft'
  if (status === 'pending_review') return 'pending'
  if (status === 'pending_payment') return 'approved'
  return status
}

export function expenseStatusLabel(status?: FinanceLedgerStatus): string {
  return ({
    draft: '草稿',
    missing_receipt: '待补发票',
    pending: '待负责人审核·已预留',
    pending_review: '待负责人审核·已预留',
    reserved: '待审核预留',
    approved: '已审核·待转账',
    pending_payment: '已审核·待转账',
    partial_paid: '部分支付',
    paid: '团队已支付',
    payment_exception: '付款异常',
    rejected: '已驳回',
    withdrawn: '已撤回',
    not_required: '无需报销',
  } as Record<string, string>)[status || 'draft'] || status || '草稿'
}

export function expenseStatusTone(
  status?: FinanceLedgerStatus,
): 'success' | 'warning' | 'danger' | 'info' | 'primary' {
  if (status === 'paid' || status === 'not_required') return 'success'
  if (status === 'payment_exception' || status === 'rejected') return 'danger'
  if (status === 'approved' || status === 'pending_payment' || status === 'partial_paid') return 'primary'
  if (status === 'pending' || status === 'pending_review' || status === 'reserved' || status === 'missing_receipt') return 'warning'
  return 'info'
}

export function incomeStageLabel(stage?: FinanceLedgerIncome['stage']): string {
  return ({
    expected: '预计奖金',
    confirmed: '已确认应收',
    received: '已到账',
  } as Record<string, string>)[stage || 'received'] || stage || '已到账'
}

export function attachmentUrl(attachment: FinanceLedgerAttachment): string {
  return attachment.file_url || attachment.file || ''
}

export function attachmentKindLabel(attachment: FinanceLedgerAttachment): string {
  if (attachment.attachment_type_display) return attachment.attachment_type_display
  return ({
    invoice: '发票',
    original_receipt: '原始票据',
    payment_proof: '转账凭证',
    income_proof: '收入到账凭证',
    transfer_proof: '内部转付凭证',
    other: '其他附件',
  } as Record<string, string>)[attachment.attachment_type || 'other']
}

export function allExpenseAttachments(expense: FinanceLedgerExpense): FinanceLedgerAttachment[] {
  const seen = new Set<number | string>()
  return [...(expense.attachments || []), ...(expense.receipts || [])].filter((item) => {
    const key = item.id || attachmentUrl(item)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function completedPaymentAmount(expense: FinanceLedgerExpense): number {
  const responseAmount = moneyNumber(expense.paid_amount)
  if (responseAmount > 0) return responseAmount
  const payments = expense.payments || []
  if (payments.length) {
    return payments
      .filter((payment) => payment.status === 'completed')
      .reduce((sum, payment) => sum + moneyNumber(payment.amount), 0)
  }
  return normalizedExpenseStatus(expense) === 'paid' ? moneyNumber(expense.amount) : 0
}

export function remainingPayable(expense: FinanceLedgerExpense): number {
  const responseAmount = moneyNumber(expense.remaining_payable ?? expense.outstanding_amount)
  if (responseAmount > 0) return responseAmount
  return Math.max(0, moneyNumber(expense.amount) - completedPaymentAmount(expense))
}

export function buildMetricSummary(
  expenses: FinanceLedgerExpense[],
  incomes: FinanceLedgerIncome[],
  response?: FinanceTraceabilitySummaryResponse | null,
): FinanceMetricSummary {
  const supplied = response?.metrics || response?.summary || {}
  const receivedFunds = incomes
    .filter((item) => (item.stage || 'received') === 'received')
    .reduce((sum, item) => sum + attributedRecordAmount(item), 0)
  const actualPaid = expenses.reduce(
    (sum, item) => sum + attributedCompletedPaymentAmount(item),
    0,
  )
  const pendingReviewReserved = expenses
    .filter((item) => ['pending', 'pending_review', 'reserved'].includes(normalizedExpenseStatus(item)))
    .reduce((sum, item) => sum + attributedRemainingPayable(item), 0)
  const approvedPendingPayment = expenses
    .filter((item) => ['approved', 'pending_payment', 'partial_paid', 'payment_exception'].includes(normalizedExpenseStatus(item)))
    .reduce((sum, item) => sum + attributedRemainingPayable(item), 0)
  const expectedBonus = incomes
    .filter((item) => item.income_type === 'bonus' && item.stage === 'expected')
    .reduce((sum, item) => sum + attributedRecordAmount(item), 0)
  const confirmedBonus = incomes
    .filter((item) => item.income_type === 'bonus' && item.stage === 'confirmed')
    .reduce((sum, item) => sum + attributedRecordAmount(item), 0)
  const value = (keys: string[], fallback: number): number => {
    for (const key of keys) {
      if (supplied[key] !== undefined) return moneyNumber(supplied[key])
    }
    return fallback
  }
  const received = value(['received_funds', 'actual_received', 'received_income'], receivedFunds)
  const reserved = value(['pending_review_reserved', 'reserved', 'pending_review'], pendingReviewReserved)
  const waiting = value(['approved_pending_payment', 'pending_payment'], approvedPendingPayment)
  const paid = value(['actual_paid', 'team_paid', 'paid'], actualPaid)
  return {
    received_funds: received,
    pending_review_reserved: reserved,
    approved_pending_payment: waiting,
    actual_paid: paid,
    expected_bonus: value(['expected_bonus'], expectedBonus),
    confirmed_bonus: value(['confirmed_bonus'], confirmedBonus),
    available_funds: value(['available_funds', 'available'], received - reserved - waiting - paid),
  }
}

const TODO_KEYS = [
  'missing_receipt',
  'pending_review',
  'pending_payment',
  'missing_payment_proof',
  'partially_paid',
  'payment_exception',
  'stale',
] as const

export function normalizeFundTodos(
  response: FinanceFundTodosResponse | null | undefined,
  expenses: FinanceLedgerExpense[],
  overdueDays = 7,
): FinanceTodoCounts {
  const groups = response?.groups || {}
  const rawSummary = response?.summary || {}
  const groupCount = (key: string, aliases: string[] = []): number | undefined => {
    for (const candidate of [key, ...aliases]) {
      if (rawSummary[candidate] !== undefined) {
        const summaryValue = rawSummary[candidate]
        if (typeof summaryValue === 'object' && summaryValue !== null) {
          return moneyNumber(summaryValue.count)
        }
        return moneyNumber(summaryValue)
      }
      const direct = (response as unknown as Record<string, unknown> | undefined)?.[candidate]
      if (Array.isArray(direct)) return direct.length
      if (Array.isArray(groups[candidate])) return groups[candidate].length
    }
    return undefined
  }
  const hasInvoice = (expense: FinanceLedgerExpense) => allExpenseAttachments(expense)
    .some((item) => ['invoice', 'original_receipt'].includes(item.attachment_type || ''))
  const payments = expenses.flatMap((item) => item.payments || [])
  const fallback: FinanceTodoCounts = {
    missing_receipt: expenses.filter((item) => !hasInvoice(item) && !['paid', 'not_required', 'withdrawn'].includes(normalizedExpenseStatus(item))).length,
    pending_review: expenses.filter((item) => ['pending', 'pending_review', 'reserved'].includes(normalizedExpenseStatus(item))).length,
    pending_payment: expenses.filter((item) => ['approved', 'pending_payment'].includes(normalizedExpenseStatus(item))).length,
    missing_payment_proof: payments.filter((item) => item.status === 'pending_proof' || (item.status === 'completed' && !(item.receipts?.length || item.proof))).length,
    partially_paid: expenses.filter((item) => normalizedExpenseStatus(item) === 'partial_paid').length,
    payment_exception: expenses.filter((item) => normalizedExpenseStatus(item) === 'payment_exception').length
      + payments.filter((item) => item.status === 'failed').length,
    stale: expenses.filter((item) => {
      if (!['pending', 'pending_review', 'approved', 'pending_payment', 'partial_paid'].includes(normalizedExpenseStatus(item))) return false
      return dayjs().diff(dayjs(item.updated_at || item.created_at), 'day') >= overdueDays
    }).length,
  }
  return TODO_KEYS.reduce((result, key) => {
    const aliases = key === 'missing_receipt'
      ? ['missing_invoice']
      : key === 'partially_paid'
        ? ['partial_payment', 'partial_paid']
        : key === 'stale'
          ? ['overdue']
          : []
    result[key] = groupCount(key, aliases) ?? fallback[key]
    return result
  }, {} as FinanceTodoCounts)
}

interface EntryIdentity {
  projectId: number | null
  projectName: string
  eventId: number | null
  eventName: string
  eventEdition: string
  entryId: number | null
  entryName: string
}

function allocationIdentity(
  allocation: FinanceLedgerAllocation,
  fallback: FinanceLedgerExpense | FinanceLedgerIncome,
): EntryIdentity {
  return {
    projectId: allocation.project ?? fallback.project,
    projectName: allocation.project_name || fallback.project_name || `项目 ${fallback.project}`,
    eventId: allocation.event ?? fallback.event ?? null,
    eventName: allocation.event_name || fallback.event_name || '项目公共支出',
    eventEdition: allocation.event_edition || fallback.event_edition || '',
    entryId: allocation.competition_entry ?? allocation.competition ?? null,
    entryName: allocation.competition_entry_name || allocation.competition_name || '项目公共',
  }
}

function directIdentity(item: FinanceLedgerExpense | FinanceLedgerIncome): EntryIdentity {
  return {
    projectId: item.project,
    projectName: item.project_name || `项目 ${item.project}`,
    eventId: item.event ?? null,
    eventName: item.event_name || '项目公共收支',
    eventEdition: item.event_edition || '',
    entryId: item.competition_entry ?? item.competition ?? null,
    entryName: item.competition_entry_name || item.competition_name || '项目公共',
  }
}

function leafKey(identity: EntryIdentity): string {
  return `${identity.projectId || 'none'}:${identity.eventId || 'common'}:${identity.entryId || 'common'}`
}

function blankLeaf(identity: EntryIdentity): FinanceTraceabilityLeaf {
  return {
    key: leafKey(identity),
    project_id: identity.projectId,
    project_name: identity.projectName,
    event_id: identity.eventId,
    event_name: identity.eventName,
    event_edition: identity.eventEdition,
    competition_entry_id: identity.entryId,
    competition_entry_name: identity.entryName,
    expected_bonus: 0,
    confirmed_bonus: 0,
    received_bonus: 0,
    member_advanced: 0,
    reserved: 0,
    paid: 0,
    outstanding: 0,
    expense_count: 0,
    income_count: 0,
    expenses: [],
    incomes: [],
  }
}

export function buildTraceabilityGroups(
  perspective: FinancePerspective,
  expenses: FinanceLedgerExpense[],
  incomes: FinanceLedgerIncome[],
): FinanceTraceabilityGroup[] {
  const leaves = new Map<string, FinanceTraceabilityLeaf>()
  const ensureLeaf = (identity: EntryIdentity) => {
    const key = leafKey(identity)
    if (!leaves.has(key)) leaves.set(key, blankLeaf(identity))
    return leaves.get(key)!
  }

  expenses.forEach((expense) => {
    const allocations = expense.allocations?.length ? expense.allocations : null
    const records = allocations || [{ ...directIdentity(expense), amount: expense.amount }]
    records.forEach((allocation) => {
      const identity = allocations
        ? allocationIdentity(allocation as FinanceLedgerAllocation, expense)
        : directIdentity(expense)
      const amount = moneyNumber((allocation as FinanceLedgerAllocation).amount ?? expense.amount)
      const ratio = moneyNumber(expense.amount) > 0 ? amount / moneyNumber(expense.amount) : 0
      const leaf = ensureLeaf(identity)
      const status = normalizedExpenseStatus(expense)
      const paid = completedPaymentAmount(expense) * ratio
      leaf.member_advanced += amount
      leaf.paid += paid
      if (!['paid', 'not_required', 'rejected', 'withdrawn'].includes(status)) {
        leaf.outstanding += Math.max(0, amount - paid)
      }
      if (['pending', 'pending_review', 'reserved', 'approved', 'pending_payment', 'partial_paid', 'payment_exception'].includes(status)) {
        leaf.reserved += Math.max(0, amount - paid)
      }
      leaf.expense_count += 1
      if (!leaf.expenses.some((item) => item.id === expense.id)) leaf.expenses.push(expense)
    })
  })

  incomes.forEach((income) => {
    const allocations = income.allocations?.length ? income.allocations : null
    const records = allocations || [{ ...directIdentity(income), amount: income.amount }]
    records.forEach((allocation) => {
      const identity = allocations
        ? allocationIdentity(allocation as FinanceLedgerAllocation, income)
        : directIdentity(income)
      const amount = moneyNumber((allocation as FinanceLedgerAllocation).amount ?? income.amount)
      const leaf = ensureLeaf(identity)
      if (income.income_type === 'bonus') {
        if (income.stage === 'expected') leaf.expected_bonus += amount
        else if (income.stage === 'confirmed') leaf.confirmed_bonus += amount
        else leaf.received_bonus += amount
      }
      leaf.income_count += 1
      if (!leaf.incomes.some((item) => item.id === income.id)) leaf.incomes.push(income)
    })
  })

  const groups = new Map<string, FinanceTraceabilityGroup>()
  Array.from(leaves.values()).forEach((leaf) => {
    const groupKey = perspective === 'project'
      ? `project:${leaf.project_id || 'none'}`
      : `event:${leaf.event_id || 'common'}`
    const label = perspective === 'project' ? leaf.project_name : leaf.event_name
    const subtitle = perspective === 'project'
      ? `${new Set([leaf.event_id].filter(Boolean)).size} 个比赛视角`
      : leaf.event_edition
    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        key: groupKey,
        label,
        subtitle,
        expected_bonus: 0,
        confirmed_bonus: 0,
        received_bonus: 0,
        member_advanced: 0,
        reserved: 0,
        paid: 0,
        outstanding: 0,
        children: [],
      })
    }
    const group = groups.get(groupKey)!
    group.children.push(leaf)
    group.expected_bonus += leaf.expected_bonus
    group.confirmed_bonus += leaf.confirmed_bonus
    group.received_bonus += leaf.received_bonus
    group.member_advanced += leaf.member_advanced
    group.reserved += leaf.reserved
    group.paid += leaf.paid
    group.outstanding += leaf.outstanding
  })

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      subtitle: perspective === 'project'
        ? `${new Set(group.children.map((item) => item.event_id).filter(Boolean)).size} 个比赛届次`
        : group.subtitle,
      children: [...group.children].sort((left, right) => (
        perspective === 'project'
          ? `${left.event_name}${left.competition_entry_name}`.localeCompare(`${right.event_name}${right.competition_entry_name}`, 'zh-CN')
          : `${left.project_name}${left.competition_entry_name}`.localeCompare(`${right.project_name}${right.competition_entry_name}`, 'zh-CN')
      )),
    }))
    .sort((left, right) => right.received_bonus + right.member_advanced - (left.received_bonus + left.member_advanced))
}

export function mergePaymentsIntoExpenses(
  expenses: FinanceLedgerExpense[],
  payments: FinanceLedgerPayment[],
): FinanceLedgerExpense[] {
  const grouped = new Map<number, FinanceLedgerPayment[]>()
  payments.forEach((payment) => {
    grouped.set(payment.expense, [...(grouped.get(payment.expense) || []), payment])
  })
  return expenses.map((expense) => ({
    ...expense,
    payments: expense.payments?.length ? expense.payments : grouped.get(expense.id) || [],
  }))
}
