import { describe, expect, it } from 'vitest'
import {
  allocationEntriesForEvent,
  allocationTargetsBelongToProject,
  allocationTargetsShareEvent,
  attributedRecordAmount,
  buildMetricSummary,
  buildTraceabilityGroups,
  filterLedgerRecordByDestination,
  normalizeFundTodos,
  resolveAllocationEventId,
} from '../financeLedger'
import type {
  FinanceLedgerExpense,
  FinanceLedgerIncome,
} from '@/types/financeLedger'

function expense(overrides: Partial<FinanceLedgerExpense> = {}): FinanceLedgerExpense {
  return {
    id: 1,
    project: 10,
    project_name: '密图项目',
    event: 20,
    event_name: '互联网+大赛',
    competition_entry: 30,
    competition_entry_name: '密图参赛队',
    category: 'travel',
    title: '现场往返车费',
    amount: 300,
    expense_date: '2026-07-20',
    reimbursement_status: 'approved',
    created_at: '2026-07-20T00:00:00Z',
    updated_at: '2026-07-20T00:00:00Z',
    ...overrides,
  }
}

function income(overrides: Partial<FinanceLedgerIncome> = {}): FinanceLedgerIncome {
  return {
    id: 1,
    project: 10,
    project_name: '密图项目',
    event: 20,
    event_name: '互联网+大赛',
    competition_entry: 30,
    competition_entry_name: '密图参赛队',
    title: '省赛奖金',
    amount: 1000,
    income_type: 'bonus',
    stage: 'expected',
    created_at: '2026-07-20T00:00:00Z',
    ...overrides,
  }
}

describe('cross-project allocation edition boundary', () => {
  const entries = [
    { id: 11, project: 1, event: 100 },
    { id: 12, project: 2, event: 100 },
    { id: 13, project: 1, event: 200 },
    { id: 14, project: 3, event: null },
  ]

  it('locks to the first selected edition and exposes entries from every project in it', () => {
    const eventId = resolveAllocationEventId(undefined, [11], entries)
    const options = allocationEntriesForEvent(entries, eventId)

    expect(eventId).toBe(100)
    expect(options.map((item) => item.id)).toEqual([11, 12])
    expect(new Set(options.map((item) => item.project))).toEqual(new Set([1, 2]))
  })

  it('accepts one-project and cross-project targets in the same edition', () => {
    expect(allocationTargetsShareEvent([11], entries, 100)).toBe(true)
    expect(allocationTargetsShareEvent([11, 12], entries, 100)).toBe(true)
  })

  it('keeps the legacy same-project mode compatible across different editions', () => {
    expect(allocationTargetsBelongToProject([11, 13], entries, 1)).toBe(true)
    expect(allocationTargetsBelongToProject([11, 12], entries, 1)).toBe(false)
  })

  it('rejects mixed editions, legacy entries without an edition and unknown entries', () => {
    expect(allocationTargetsShareEvent([11, 13], entries, 100)).toBe(false)
    expect(allocationTargetsShareEvent([14], entries)).toBe(false)
    expect(allocationTargetsShareEvent([999], entries, 100)).toBe(false)
  })

  it('filters by allocation destination project and removes unrelated shares', () => {
    const record = expense({
      project: 1,
      allocations: [
        { competition_entry: 11, project: 1, event: 100, amount: 40 },
        { competition_entry: 12, project: 2, event: 100, amount: 60 },
      ],
    })

    expect(filterLedgerRecordByDestination(record, 2)?.allocations).toEqual([
      { competition_entry: 12, project: 2, event: 100, amount: 60 },
    ])
    expect(filterLedgerRecordByDestination(record, 3)).toBeNull()
    expect(filterLedgerRecordByDestination(record, 2, 200)).toBeNull()
  })

  it('uses only the retained destination share in fallback metrics', () => {
    const allocatedExpense = filterLedgerRecordByDestination(expense({
      project: 1,
      amount: 100,
      reimbursement_status: 'paid',
      payments: [{ id: 1, expense: 1, amount: 100, status: 'completed' }],
      allocations: [
        { competition_entry: 11, project: 1, event: 100, amount: 40 },
        { competition_entry: 12, project: 2, event: 100, amount: 60 },
      ],
    }), 2)
    const allocatedIncome = filterLedgerRecordByDestination(income({
      project: 1,
      amount: 100,
      stage: 'received',
      allocations: [
        { competition_entry: 11, project: 1, event: 100, amount: 40 },
        { competition_entry: 12, project: 2, event: 100, amount: 60 },
      ],
    }), 2)

    expect(allocatedExpense).not.toBeNull()
    expect(allocatedIncome).not.toBeNull()
    expect(attributedRecordAmount(allocatedExpense!)).toBe(60)
    const metrics = buildMetricSummary(
      [allocatedExpense!],
      [allocatedIncome!],
    )
    expect(metrics.received_funds).toBe(60)
    expect(metrics.actual_paid).toBe(60)
    expect(metrics.available_funds).toBe(0)
  })
})

describe('finance ledger metrics', () => {
  it('counts only received income as available funds and only completed payments as actual paid', () => {
    const expenses = [
      expense({ id: 1, amount: 200, reimbursement_status: 'pending' }),
      expense({
        id: 2,
        amount: 300,
        reimbursement_status: 'partial_paid',
        payments: [
          { id: 1, expense: 2, amount: 100, status: 'completed' },
          { id: 2, expense: 2, amount: 50, status: 'pending_proof' },
        ],
      }),
    ]
    const incomes = [
      income({ id: 1, amount: 500, stage: 'expected' }),
      income({ id: 2, amount: 700, stage: 'confirmed' }),
      income({ id: 3, amount: 2000, stage: 'received' }),
    ]

    expect(buildMetricSummary(expenses, incomes)).toEqual({
      received_funds: 2000,
      pending_review_reserved: 200,
      approved_pending_payment: 200,
      actual_paid: 100,
      expected_bonus: 500,
      confirmed_bonus: 700,
      available_funds: 1500,
    })
  })
})

describe('dual traceability grouping', () => {
  const allocatedExpense = expense({
    id: 7,
    competition_entry: null,
    event: null,
    amount: 300,
    payments: [{ id: 10, expense: 7, amount: 150, status: 'completed' }],
    allocations: [
      { competition_entry: 31, competition_entry_name: 'A队', event: 20, event_name: '互联网+大赛', amount: 100 },
      { competition_entry: 32, competition_entry_name: 'B队', event: 21, event_name: '挑战杯', amount: 200 },
    ],
  })
  const allocatedIncome = income({
    id: 8,
    competition_entry: null,
    event: null,
    amount: 600,
    stage: 'received',
    allocations: [
      { competition_entry: 31, competition_entry_name: 'A队', event: 20, event_name: '互联网+大赛', amount: 200 },
      { competition_entry: 32, competition_entry_name: 'B队', event: 21, event_name: '挑战杯', amount: 400 },
    ],
  })

  it('shows one project with multiple competition entries without double counting allocations', () => {
    const groups = buildTraceabilityGroups('project', [allocatedExpense], [allocatedIncome])

    expect(groups).toHaveLength(1)
    expect(groups[0].children).toHaveLength(2)
    expect(groups[0].member_advanced).toBe(300)
    expect(groups[0].paid).toBe(150)
    expect(groups[0].received_bonus).toBe(600)
  })

  it('shows the same ledger as separate competition groups', () => {
    const groups = buildTraceabilityGroups('competition', [allocatedExpense], [allocatedIncome])

    expect(groups.map((group) => group.label).sort()).toEqual(['互联网+大赛', '挑战杯'].sort())
    expect(groups.reduce((sum, group) => sum + group.received_bonus, 0)).toBe(600)
    expect(groups.reduce((sum, group) => sum + group.member_advanced, 0)).toBe(300)
  })
})

describe('finance todo fallback', () => {
  it('identifies missing invoices, pending review, partial payment and failed payments', () => {
    const expenses = [
      expense({ id: 1, reimbursement_status: 'pending', receipts: [] }),
      expense({
        id: 2,
        reimbursement_status: 'partial_paid',
        receipts: [{ id: 2, expense: 2, attachment_type: 'invoice', file: '/invoice.pdf' }],
        payments: [{ id: 3, expense: 2, amount: 50, status: 'failed' }],
      }),
    ]

    const todos = normalizeFundTodos(undefined, expenses)

    expect(todos.missing_receipt).toBe(1)
    expect(todos.pending_review).toBe(1)
    expect(todos.partially_paid).toBe(1)
    expect(todos.payment_exception).toBe(1)
  })

  it('reads count objects returned by the operational todo endpoint', () => {
    const todos = normalizeFundTodos({
      summary: {
        missing_invoice: { count: 4, amount: '300.00' },
        pending_review: { count: 2, amount: '120.00' },
      },
    }, [])

    expect(todos.missing_receipt).toBe(4)
    expect(todos.pending_review).toBe(2)
  })
})
