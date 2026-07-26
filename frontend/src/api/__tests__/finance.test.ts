import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { FinanceBudget, FinanceExpense, PaginatedResponse } from '@/types'

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
  upload: vi.fn(),
}))

import {
  getAllFinanceExpenses,
  getFinanceBudgetByProject,
  resolveFinanceExportTarget,
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
