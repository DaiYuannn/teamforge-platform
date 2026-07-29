import { get, post, patch, del, upload } from './request'
import type {
  FinanceBudget,
  FinanceExpense,
  FinanceExpenseFormData,
  FinanceIncome,
  FinanceIncomeFormData,
  FinanceReceipt,
  PaginatedResponse,
  PaginationParams,
} from '@/types'
import type {
  FinanceAllocationInput,
  FinanceExpenseInput,
  FinanceIncomeInput,
  FinanceInternalTransfer,
  FinanceLedgerAttachment,
  FinanceLedgerExpense,
  FinanceLedgerIncome,
  FinanceLedgerPayment,
  FinancePaymentInput,
  FinancePerspective,
  FinanceTimelineEvent,
} from '@/types/financeLedger'

/** 预算查询参数（后端 filterset: project / status / period） */
export interface BudgetQueryParams extends PaginationParams {
  project?: number
  status?: string
  period?: string
}

/** 支出查询参数（后端 filterset: project / category / spender / expense_date） */
export interface ExpenseQueryParams extends PaginationParams {
  project?: number
  event?: number
  competition_entry?: number
  category?: string
  spender?: number
  expense_date?: string
  reimbursement_status?: string
}

export interface IncomeQueryParams extends PaginationParams {
  project?: number
  event?: number
  competition_entry?: number
  income_type?: string
  stage?: string
  income_date?: string
}

const FINANCE_PAGE_SIZE = 100

async function getAllFinancePages<T, P extends PaginationParams>(
  path: string,
  params: P,
): Promise<T[]> {
  const firstPage = await get<PaginatedResponse<T> | T[]>(path, {
    ...params,
    page: 1,
    page_size: FINANCE_PAGE_SIZE,
  })
  if (Array.isArray(firstPage)) return firstPage

  const pageCount = Math.ceil(firstPage.count / FINANCE_PAGE_SIZE)
  if (pageCount <= 1) return firstPage.results

  const remainingPages = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) =>
      get<PaginatedResponse<T>>(path, {
        ...params,
        page: index + 2,
        page_size: FINANCE_PAGE_SIZE,
      }),
    ),
  )
  return [firstPage, ...remainingPages].flatMap((page) => page.results)
}

/** 获取经费预算列表 */
export function getFinanceBudgets(params: BudgetQueryParams): Promise<PaginatedResponse<FinanceBudget>> {
  return get<PaginatedResponse<FinanceBudget>>('/finance/budgets/', params)
}

/** 获取符合筛选条件的全部经费预算 */
export function getAllFinanceBudgets(params: BudgetQueryParams = {}): Promise<FinanceBudget[]> {
  return getAllFinancePages<FinanceBudget, BudgetQueryParams>('/finance/budgets/', params)
}

/** 按项目获取经费预算 */
export function getFinanceBudgetByProject(projectId: number): Promise<FinanceBudget[]> {
  return getAllFinanceBudgets({ project: projectId })
}

export function createFinanceBudget(data: {
  project: number
  planned_amount: number
  period?: string
}): Promise<FinanceBudget> {
  return post<FinanceBudget>('/finance/budgets/', data)
}

export function updateFinanceBudget(
  id: number,
  data: { planned_amount: number; period?: string },
): Promise<FinanceBudget> {
  return patch<FinanceBudget>(`/finance/budgets/${id}/`, data)
}

/** 获取经费支出列表 */
export function getFinanceExpenses(params: ExpenseQueryParams): Promise<PaginatedResponse<FinanceExpense>> {
  return get<PaginatedResponse<FinanceExpense>>('/finance/expenses/', params)
}

/** 获取符合筛选条件的全部经费支出 */
export function getAllFinanceExpenses(params: ExpenseQueryParams = {}): Promise<FinanceExpense[]> {
  return getAllFinancePages<FinanceExpense, ExpenseQueryParams>('/finance/expenses/', params)
}

/** 按项目获取经费支出 */
export function getFinanceExpensesByProject(projectId: number): Promise<FinanceExpense[]> {
  return getAllFinanceExpenses({ project: projectId })
}

/** 获取收入流水。 */
export function getFinanceIncomes(params: IncomeQueryParams): Promise<PaginatedResponse<FinanceIncome>> {
  return get<PaginatedResponse<FinanceIncome>>('/finance/incomes/', params)
}

export function getAllFinanceIncomes(params: IncomeQueryParams = {}): Promise<FinanceIncome[]> {
  return getAllFinancePages<FinanceIncome, IncomeQueryParams>('/finance/incomes/', params)
}

export function createFinanceIncome(data: FinanceIncomeFormData | FinanceIncomeInput): Promise<FinanceLedgerIncome> {
  return post<FinanceLedgerIncome>('/finance/incomes/', data)
}

export function updateFinanceIncome(id: number, data: Partial<FinanceIncomeFormData>): Promise<FinanceIncome> {
  return patch<FinanceIncome>(`/finance/incomes/${id}/`, data)
}

export function deleteFinanceIncome(id: number): Promise<void> {
  return del<void>(`/finance/incomes/${id}/`)
}

export type FinanceExportFormat = 'xlsx' | 'pdf'

export interface FinanceExportTarget {
  type: 'finance_budget' | 'finance_detail' | 'finance_report'
  projectId?: number
}

/** 将经费页导出操作映射到后端实际支持的导出契约。 */
export function resolveFinanceExportTarget(
  format: FinanceExportFormat,
  projectId?: number,
): FinanceExportTarget {
  if (format === 'pdf') return { type: 'finance_report', projectId }
  if (projectId) return { type: 'finance_detail', projectId }
  return { type: 'finance_budget' }
}

/** 创建经费支出 */
export function createFinanceExpense(data: FinanceExpenseFormData | FinanceExpenseInput): Promise<FinanceLedgerExpense> {
  return post<FinanceLedgerExpense>('/finance/expenses/', data)
}

/** 更新经费支出 */
export function updateFinanceExpense(id: number, data: Partial<FinanceExpenseFormData>): Promise<FinanceExpense> {
  return patch<FinanceExpense>(`/finance/expenses/${id}/`, data)
}

/** 删除经费支出 */
export function deleteFinanceExpense(id: number): Promise<void> {
  return del<void>(`/finance/expenses/${id}/`)
}

export function submitReimbursement(id: number): Promise<FinanceExpense> {
  return post<FinanceExpense>(`/finance/expenses/${id}/submit_reimbursement/`, {})
}

export function reviewReimbursement(
  id: number,
  approved: boolean,
  opinion = '',
): Promise<FinanceExpense> {
  return post<FinanceExpense>(`/finance/expenses/${id}/review_reimbursement/`, {
    approved,
    opinion,
  })
}

export function markReimbursementPaid(
  id: number,
  payment_method: string,
  payment_reference = '',
  proofFile?: File,
): Promise<FinanceExpense> {
  const formData = new FormData()
  formData.append('payment_method', payment_method)
  formData.append('payment_reference', payment_reference)
  if (proofFile) formData.append('proof_file', proofFile)
  return upload<FinanceExpense>(`/finance/expenses/${id}/mark_paid/`, formData)
}

/** 上传经费票据 */
export function uploadReceipt(expenseId: number, file: File): Promise<FinanceReceipt> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('expense', String(expenseId))
  return upload<FinanceReceipt>('/finance/receipts/', formData)
}

/** 获取经费票据列表 */
export function getReceipts(expenseId: number): Promise<FinanceReceipt[]> {
  return get<FinanceReceipt[]>('/finance/receipts/', { expense: expenseId })
}

export interface FinancePaymentQueryParams extends PaginationParams {
  expense?: number
  recipient?: number
  status?: string
}

export interface FinanceTransferQueryParams extends PaginationParams {
  project?: number
  competition_entry?: number
  from_user?: number
  to_user?: number
  status?: string
}

export interface FinanceTraceabilityQuery {
  perspective?: FinancePerspective
  project?: number
  event?: number
}

export interface FinanceTraceabilitySummaryResponse {
  perspective?: FinancePerspective
  metrics?: Record<string, number | string>
  summary?: Record<string, number | string>
  groups?: unknown[]
  rows?: unknown[]
  project_rows?: unknown[]
  competition_rows?: unknown[]
  can_manage?: boolean
  can_register_income?: boolean
  can_create_expense?: boolean
}

export interface FinanceFundTodoItem {
  id: number | string
  expense?: number
  payment?: number
  title?: string
  project_name?: string
  competition_entry_name?: string
  amount?: number | string
  status?: string
  due_at?: string | null
  created_at?: string
}

export interface FinanceFundTodosResponse {
  summary?: Record<string, number | { count?: number; amount?: number | string }>
  groups?: Record<string, FinanceFundTodoItem[]>
  missing_invoice?: FinanceFundTodoItem[]
  pending_review?: FinanceFundTodoItem[]
  pending_payment?: FinanceFundTodoItem[]
  missing_payment_proof?: FinanceFundTodoItem[]
  partial_payment?: FinanceFundTodoItem[]
  payment_exception?: FinanceFundTodoItem[]
  overdue?: FinanceFundTodoItem[]
}

export function setExpenseAllocations(
  id: number,
  allocations: FinanceAllocationInput[],
): Promise<FinanceLedgerExpense> {
  return post<FinanceLedgerExpense>(`/finance/expenses/${id}/set_allocations/`, { allocations })
}

export function setIncomeAllocations(
  id: number,
  allocations: FinanceAllocationInput[],
): Promise<FinanceLedgerIncome> {
  return post<FinanceLedgerIncome>(`/finance/incomes/${id}/set_allocations/`, { allocations })
}

export function setFinanceIncomeStage(
  id: number,
  stage: FinanceLedgerIncome['stage'],
  proofFile?: File,
): Promise<FinanceLedgerIncome> {
  const formData = new FormData()
  if (stage) formData.append('stage', stage)
  if (proofFile) formData.append('proof_file', proofFile)
  return upload<FinanceLedgerIncome>(`/finance/incomes/${id}/set_stage/`, formData)
}

export function getFinancePayments(
  params: FinancePaymentQueryParams = {},
): Promise<PaginatedResponse<FinanceLedgerPayment> | FinanceLedgerPayment[]> {
  return get('/finance/payments/', params)
}

export function getAllFinancePayments(
  params: FinancePaymentQueryParams = {},
): Promise<FinanceLedgerPayment[]> {
  return getAllFinancePages<FinanceLedgerPayment, FinancePaymentQueryParams>('/finance/payments/', params)
}

export function createFinancePayment(data: FinancePaymentInput): Promise<FinanceLedgerPayment> {
  const formData = new FormData()
  formData.append('expense', String(data.expense))
  formData.append('recipient', String(data.recipient))
  formData.append('amount', String(data.amount))
  formData.append('status', data.status || 'completed')
  formData.append('payment_method', data.payment_method)
  formData.append('payment_reference', data.payment_reference)
  if (data.payment_date) formData.append('payment_date', data.payment_date)
  if (data.failure_reason) formData.append('failure_reason', data.failure_reason)
  if (data.proof) formData.append('proof_file', data.proof)
  return upload<FinanceLedgerPayment>('/finance/payments/', formData)
}

export function completeFinancePayment(
  id: number,
  data: Omit<FinancePaymentInput, 'expense' | 'status'>,
): Promise<FinanceLedgerPayment> {
  const formData = new FormData()
  formData.append('recipient', String(data.recipient))
  formData.append('amount', String(data.amount))
  formData.append('payment_method', data.payment_method)
  formData.append('payment_reference', data.payment_reference)
  if (data.payment_date) formData.append('payment_date', data.payment_date)
  if (data.proof) formData.append('proof_file', data.proof)
  return upload<FinanceLedgerPayment>(`/finance/payments/${id}/complete/`, formData)
}

export function failFinancePayment(id: number, failureReason: string): Promise<FinanceLedgerPayment> {
  return post<FinanceLedgerPayment>(`/finance/payments/${id}/fail/`, {
    failure_reason: failureReason,
  })
}

export function getFinanceTransfers(
  params: FinanceTransferQueryParams = {},
): Promise<PaginatedResponse<FinanceInternalTransfer> | FinanceInternalTransfer[]> {
  return get('/finance/transfers/', params)
}

export function createFinanceTransfer(data: {
  project: number
  competition_entry?: number | null
  from_user?: number | null
  to_user: number
  source_label?: string
  amount: number
  status: FinanceInternalTransfer['status']
  payment_method?: string
  payment_reference?: string
  transfer_date?: string
  failure_reason?: string
  note?: string
  proof_file?: File
}): Promise<FinanceInternalTransfer> {
  const formData = new FormData()
  Object.entries(data).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    formData.append(key, value instanceof File ? value : String(value))
  })
  return upload<FinanceInternalTransfer>('/finance/transfers/', formData)
}

export function completeFinanceTransfer(
  id: number,
  proofFile: File,
  transferDate?: string,
  paymentReference?: string,
): Promise<FinanceInternalTransfer> {
  const formData = new FormData()
  formData.append('proof_file', proofFile)
  if (transferDate) formData.append('transfer_date', transferDate)
  if (paymentReference) formData.append('payment_reference', paymentReference)
  return upload<FinanceInternalTransfer>(`/finance/transfers/${id}/complete/`, formData)
}

export function failFinanceTransfer(id: number, failureReason: string): Promise<FinanceInternalTransfer> {
  return post<FinanceInternalTransfer>(`/finance/transfers/${id}/fail/`, {
    failure_reason: failureReason,
  })
}

export function getFinanceTraceabilitySummary(
  params: FinanceTraceabilityQuery,
): Promise<FinanceTraceabilitySummaryResponse> {
  return get<FinanceTraceabilitySummaryResponse>('/finance/traceability/summary/', params)
}

export function getFinanceTraceabilityDetail(competitionEntry: number): Promise<Record<string, unknown>> {
  return get('/finance/traceability/detail/', { competition_entry: competitionEntry })
}

export function getFinanceTimeline(params: {
  expense?: number
  income?: number
  payment?: number
  transfer?: number
}): Promise<FinanceTimelineEvent[]> {
  return get<FinanceTimelineEvent[]>('/finance/traceability/timeline/', params)
}

export function getFinanceFundTodos(overdueDays = 7): Promise<FinanceFundTodosResponse> {
  return get<FinanceFundTodosResponse>('/finance/fund-todos/', { overdue_days: overdueDays })
}

export function uploadFinanceAttachment(data: {
  file: File
  attachment_type: FinanceLedgerAttachment['attachment_type']
  expense?: number
  income?: number
  payment?: number
  internal_transfer?: number
}): Promise<FinanceLedgerAttachment> {
  const formData = new FormData()
  formData.append('file', data.file)
  if (data.attachment_type) formData.append('attachment_type', data.attachment_type)
  for (const owner of ['expense', 'income', 'payment', 'internal_transfer'] as const) {
    if (data[owner]) formData.append(owner, String(data[owner]))
  }
  return upload<FinanceLedgerAttachment>('/finance/receipts/', formData)
}

export interface OCRRecognizedReceipt {
  amount: string | null
  expense_date: string
  category: string
  title: string
  vendor: string
  invoice_number: string
  confidence: number
  field_confidence: Record<string, number>
  warnings: string[]
}

export interface OCRReceiptResult {
  success: boolean
  is_stub: false
  engine: 'tesseract'
  message: string
  file_info: {
    name: string
    size: number
    content_type: string
    width: number
    height: number
  }
  recognized: OCRRecognizedReceipt
  raw_text: string
}

/** 使用服务器本地 Tesseract 识别票据。 */
export function recognizeReceipt(file: File): Promise<OCRReceiptResult> {
  const formData = new FormData()
  formData.append('image', file)
  return upload<OCRReceiptResult>('/finance/ocr/recognize/', formData)
}
