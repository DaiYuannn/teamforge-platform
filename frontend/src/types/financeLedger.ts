import type { FinanceCategory } from './index'

export type FinancePerspective = 'project' | 'competition'

export type FinanceIncomeStage = 'expected' | 'confirmed' | 'received'

export type FinanceLedgerStatus =
  | 'draft'
  | 'missing_receipt'
  | 'pending'
  | 'pending_review'
  | 'reserved'
  | 'approved'
  | 'pending_payment'
  | 'partial_paid'
  | 'paid'
  | 'payment_exception'
  | 'rejected'
  | 'withdrawn'
  | 'not_required'

export type FinanceAttachmentKind =
  | 'invoice'
  | 'original_receipt'
  | 'payment_proof'
  | 'income_proof'
  | 'transfer_proof'
  | 'other'

export type FinanceScope = 'competition_entry' | 'project_common' | 'allocated'

export interface FinanceLedgerAttachment {
  id: number
  expense?: number | null
  income?: number | null
  payment?: number | null
  internal_transfer?: number | null
  attachment_type?: FinanceAttachmentKind
  attachment_type_display?: string
  file?: string
  file_url?: string
  file_name?: string
  uploaded_by?: number | null
  uploaded_by_name?: string
  created_at?: string
}

export interface FinanceLedgerAllocation {
  id?: number
  expense?: number | null
  income?: number | null
  competition?: number | null
  competition_entry?: number | null
  competition_name?: string
  competition_entry_name?: string
  event?: number | null
  event_name?: string
  event_edition?: string
  project?: number | null
  project_name?: string
  amount: number | string
  note?: string
}

/** Write payload for assigning one ledger record to a competition entry. */
export interface FinanceAllocationInput {
  competition_entry: number
  amount: number | string
  note?: string
}

export interface FinanceLedgerPayment {
  id: number
  expense: number
  amount: number | string
  recipient?: number | null
  recipient_name?: string
  payment_method?: string
  payment_reference?: string
  expense_title?: string
  project?: number
  project_name?: string
  paid_at?: string | null
  status?: 'pending_proof' | 'completed' | 'failed' | 'reversed'
  status_display?: string
  failure_reason?: string
  paid_by?: number | null
  paid_by_name?: string
  proof?: FinanceLedgerAttachment | null
  receipts?: FinanceLedgerAttachment[]
  attachments?: FinanceLedgerAttachment[]
  created_at?: string
  updated_at?: string
}

export interface FinanceTimelineEvent {
  id: string | number
  action?: string
  action_display?: string
  title: string
  description?: string
  operator?: number | null
  operator_name?: string
  occurred_at?: string
  created_at?: string
  metadata?: Record<string, unknown>
}

export interface FinanceLedgerExpense {
  id: number
  project: number
  project_name?: string
  competition?: number | null
  competition_entry?: number | null
  competition_name?: string
  competition_entry_name?: string
  event?: number | null
  event_name?: string
  event_edition?: string
  scope?: FinanceScope
  category: FinanceCategory
  category_display?: string
  title: string
  purpose?: string
  amount: number | string
  expense_date: string
  spender?: number | null
  spender_name?: string
  payee?: number | null
  payee_name?: string
  applied_by?: number | null
  applied_by_name?: string
  applied_at?: string | null
  reviewer?: number | null
  reviewer_name?: string
  reviewed_at?: string | null
  review_opinion?: string
  reimbursement_status?: FinanceLedgerStatus
  reimbursement_status_display?: string
  reserved_amount?: number | string
  paid_amount?: number | string
  outstanding_amount?: number | string
  remaining_payable?: number | string
  payment_method?: string
  payment_reference?: string
  paid_by?: number | null
  paid_by_name?: string
  paid_at?: string | null
  receipts?: FinanceLedgerAttachment[]
  attachments?: FinanceLedgerAttachment[]
  payments?: FinanceLedgerPayment[]
  allocations?: FinanceLedgerAllocation[]
  timeline?: FinanceTimelineEvent[]
  can_submit?: boolean
  can_review?: boolean
  can_pay?: boolean
  can_manage?: boolean
  created_at: string
  updated_at?: string
}

export interface FinanceLedgerIncome {
  id: number
  project: number
  project_name?: string
  competition?: number | null
  competition_entry?: number | null
  competition_name?: string
  competition_entry_name?: string
  event?: number | null
  event_name?: string
  event_edition?: string
  title: string
  amount: number | string
  income_type: 'bonus' | 'grant' | 'sponsorship' | 'refund' | 'other'
  income_type_display?: string
  stage?: FinanceIncomeStage
  stage_display?: string
  income_date?: string | null
  expected_date?: string | null
  confirmed_date?: string | null
  received_date?: string | null
  confirmed_at?: string | null
  received_at?: string | null
  source?: string
  reference_number?: string
  note?: string
  recorded_by?: number | null
  recorded_by_name?: string
  receipts?: FinanceLedgerAttachment[]
  attachments?: FinanceLedgerAttachment[]
  allocations?: FinanceLedgerAllocation[]
  timeline?: FinanceTimelineEvent[]
  can_manage?: boolean
  created_at: string
  updated_at?: string
}

export interface FinanceTodoCounts {
  missing_receipt: number
  pending_review: number
  pending_payment: number
  missing_payment_proof: number
  partially_paid: number
  payment_exception: number
  stale: number
}

export interface FinanceMetricSummary {
  received_funds: number
  pending_review_reserved: number
  approved_pending_payment: number
  actual_paid: number
  expected_bonus: number
  confirmed_bonus: number
  available_funds: number
}

export interface FinanceTraceabilityLeaf {
  key: string
  project_id?: number | null
  project_name: string
  event_id?: number | null
  event_name: string
  event_edition?: string
  competition_entry_id?: number | null
  competition_entry_name: string
  participant_names?: string[]
  leader_names?: string[]
  award_result?: string
  expected_bonus: number
  confirmed_bonus: number
  received_bonus: number
  member_advanced: number
  reserved: number
  paid: number
  outstanding: number
  expense_count: number
  income_count: number
  expenses: FinanceLedgerExpense[]
  incomes: FinanceLedgerIncome[]
}

export interface FinanceTraceabilityGroup {
  key: string
  label: string
  subtitle?: string
  expected_bonus: number
  confirmed_bonus: number
  received_bonus: number
  member_advanced: number
  reserved: number
  paid: number
  outstanding: number
  children: FinanceTraceabilityLeaf[]
}

export interface FinancePaymentInput {
  expense: number
  amount: number
  recipient: number
  payment_method: string
  payment_reference: string
  payment_date?: string
  status?: 'pending_proof' | 'completed'
  failure_reason?: string
  proof?: File
}

export interface FinanceInternalTransfer {
  id: number
  project: number
  project_name?: string
  competition_entry?: number | null
  competition_entry_name?: string
  from_user?: number | null
  from_user_name?: string
  to_user: number
  to_user_name?: string
  source_label?: string
  amount: number | string
  status: 'pending_proof' | 'completed' | 'failed'
  status_display?: string
  payment_method?: string
  payment_reference?: string
  transferred_at?: string | null
  failure_reason?: string
  note?: string
  receipts?: FinanceLedgerAttachment[]
  can_manage?: boolean
  created_at: string
  updated_at?: string
}

export interface FinanceExpenseInput {
  project: number
  competition_entry?: number | null
  scope: FinanceScope
  category: FinanceCategory
  title: string
  purpose?: string
  amount: number
  expense_date: string
  spender?: number | null
  payee?: number | null
}

export interface FinanceIncomeInput {
  project: number
  competition_entry?: number | null
  title: string
  amount: number
  income_type: FinanceLedgerIncome['income_type']
  stage: FinanceIncomeStage
  income_date?: string | null
  expected_date?: string | null
  confirmed_date?: string | null
  received_date?: string | null
  source?: string
  reference_number?: string
  note?: string
}
