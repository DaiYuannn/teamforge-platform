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

/** 预算查询参数（后端 filterset: project / status / period） */
export interface BudgetQueryParams extends PaginationParams {
  project?: number
  status?: string
  period?: string
}

/** 支出查询参数（后端 filterset: project / category / spender / expense_date） */
export interface ExpenseQueryParams extends PaginationParams {
  project?: number
  category?: string
  spender?: number
  expense_date?: string
  reimbursement_status?: string
}

export interface IncomeQueryParams extends PaginationParams {
  project?: number
  income_type?: string
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

export function createFinanceIncome(data: FinanceIncomeFormData): Promise<FinanceIncome> {
  return post<FinanceIncome>('/finance/incomes/', data)
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
export function createFinanceExpense(data: FinanceExpenseFormData): Promise<FinanceExpense> {
  return post<FinanceExpense>('/finance/expenses/', data)
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
): Promise<FinanceExpense> {
  return post<FinanceExpense>(`/finance/expenses/${id}/mark_paid/`, {
    payment_method,
    payment_reference,
  })
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
