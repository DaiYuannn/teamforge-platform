import { get, post, patch, del, upload } from './request'
import type {
  FinanceBudget,
  FinanceExpense,
  FinanceExpenseFormData,
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
}

/** 获取经费预算列表 */
export function getFinanceBudgets(params: BudgetQueryParams): Promise<PaginatedResponse<FinanceBudget>> {
  return get<PaginatedResponse<FinanceBudget>>('/finance/budgets/', params)
}

/** 按项目获取经费预算 */
export function getFinanceBudgetByProject(projectId: number): Promise<FinanceBudget[]> {
  return get<FinanceBudget[]>('/finance/budgets/', { project: projectId, page_size: 999 })
}

/** 获取经费支出列表 */
export function getFinanceExpenses(params: ExpenseQueryParams): Promise<PaginatedResponse<FinanceExpense>> {
  return get<PaginatedResponse<FinanceExpense>>('/finance/expenses/', params)
}

/** 按项目获取经费支出 */
export function getFinanceExpensesByProject(projectId: number): Promise<FinanceExpense[]> {
  return get<FinanceExpense[]>('/finance/expenses/', { project: projectId, page_size: 999 })
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
