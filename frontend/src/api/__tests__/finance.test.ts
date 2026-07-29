import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { FinanceBudget, FinanceExpense, PaginatedResponse } from '@/types'

const { getMock, postMock, uploadMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  uploadMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: postMock,
  patch: vi.fn(),
  del: vi.fn(),
  upload: uploadMock,
}))

import {
  createFinancePayment,
  getFinanceFundTodos,
  getFinanceTraceabilitySummary,
  getAllFinanceExpenses,
  getFinanceBudgetByProject,
  resolveFinanceExportTarget,
  setExpenseAllocations,
  setFinanceIncomeStage,
} from '@/api/finance'

function page<T>(count: number, results: T[]): PaginatedResponse<T> {
  return {
    count,
    next: count > results.length ? '/next/' : null,
    previous: null,
    results,
  }
}

function expense(id: number): FinanceExpense {
  return {
    id,
    project: 7,
    category: 'material',
    amount: id,
    title: `支出 ${id}`,
    expense_date: '2026-07-24',
    created_at: '2026-07-24T00:00:00Z',
    updated_at: '2026-07-24T00:00:00Z',
  }
}

beforeEach(() => {
  getMock.mockReset()
  postMock.mockReset()
  uploadMock.mockReset()
})

describe('finance pagination helpers', () => {
  it('loads every expense page while preserving filters', async () => {
    getMock
      .mockResolvedValueOnce(page(201, [expense(1)]))
      .mockResolvedValueOnce(page(201, [expense(2)]))
      .mockResolvedValueOnce(page(201, [expense(3)]))

    await expect(getAllFinanceExpenses({ project: 7 })).resolves.toEqual([
      expense(1),
      expense(2),
      expense(3),
    ])
    expect(getMock).toHaveBeenNthCalledWith(1, '/finance/expenses/', {
      project: 7,
      page: 1,
      page_size: 100,
    })
    expect(getMock).toHaveBeenNthCalledWith(2, '/finance/expenses/', {
      project: 7,
      page: 2,
      page_size: 100,
    })
    expect(getMock).toHaveBeenNthCalledWith(3, '/finance/expenses/', {
      project: 7,
      page: 3,
      page_size: 100,
    })
  })

  it('keeps compatibility with an unpaginated project budget response', async () => {
    const budget = { id: 9, project: 7 } as FinanceBudget
    getMock.mockResolvedValueOnce([budget])

    await expect(getFinanceBudgetByProject(7)).resolves.toEqual([budget])
  })
})

describe('finance export contract', () => {
  it('uses the global budget export for an unfiltered Excel download', () => {
    expect(resolveFinanceExportTarget('xlsx')).toEqual({ type: 'finance_budget' })
  })

  it('uses project detail export for a filtered Excel download', () => {
    expect(resolveFinanceExportTarget('xlsx', 7)).toEqual({
      type: 'finance_detail',
      projectId: 7,
    })
  })

  it('uses the finance report export for PDF', () => {
    expect(resolveFinanceExportTarget('pdf', 7)).toEqual({
      type: 'finance_report',
      projectId: 7,
    })
  })
})

describe('traceable finance workflow contract', () => {
  it('replaces expense allocations only after the parent record exists', async () => {
    postMock.mockResolvedValueOnce({ id: 12 })

    await setExpenseAllocations(12, [
      { competition_entry: 31, amount: 75, note: '车费' },
      { competition_entry: 32, amount: 25, note: '材料' },
    ])

    expect(postMock).toHaveBeenCalledWith('/finance/expenses/12/set_allocations/', {
      allocations: [
        { competition_entry: 31, amount: 75, note: '车费' },
        { competition_entry: 32, amount: 25, note: '材料' },
      ],
    })
  })

  it('requires the caller to send the transfer proof when completing a payment', async () => {
    const proof = new File(['proof'], 'transfer.png', { type: 'image/png' })
    uploadMock.mockResolvedValueOnce({ id: 8 })

    await createFinancePayment({
      expense: 12,
      recipient: 9,
      amount: 88.5,
      status: 'completed',
      payment_method: '银行转账',
      payment_reference: 'TX-001',
      payment_date: '2026-07-29T13:00:00',
      proof,
    })

    expect(uploadMock).toHaveBeenCalledWith('/finance/payments/', expect.any(FormData))
    const payload = uploadMock.mock.calls[0]?.[1] as FormData
    expect(payload.get('expense')).toBe('12')
    expect(payload.get('status')).toBe('completed')
    expect(payload.get('payment_reference')).toBe('TX-001')
    expect(payload.get('payment_date')).toBe('2026-07-29T13:00:00')
    expect(payload.get('proof_file')).toBe(proof)
  })

  it('advances received income through multipart so an arrival proof can be archived', async () => {
    const proof = new File(['income'], 'arrival.pdf', { type: 'application/pdf' })
    uploadMock.mockResolvedValueOnce({ id: 5, stage: 'received' })

    await setFinanceIncomeStage(5, 'received', proof)

    expect(uploadMock).toHaveBeenCalledWith('/finance/incomes/5/set_stage/', expect.any(FormData))
    const payload = uploadMock.mock.calls[0]?.[1] as FormData
    expect(payload.get('stage')).toBe('received')
    expect(payload.get('proof_file')).toBe(proof)
  })

  it('loads both traceability perspectives and operational todos from dedicated endpoints', async () => {
    getMock.mockResolvedValue({})

    await getFinanceTraceabilitySummary({ perspective: 'competition', project: 7, event: 4 })
    await getFinanceFundTodos(10)

    expect(getMock).toHaveBeenNthCalledWith(1, '/finance/traceability/summary/', {
      perspective: 'competition',
      project: 7,
      event: 4,
    })
    expect(getMock).toHaveBeenNthCalledWith(2, '/finance/fund-todos/', { overdue_days: 10 })
  })
})
