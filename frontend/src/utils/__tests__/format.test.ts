import { afterEach, describe, it, expect, vi } from 'vitest'
import {
  downloadBlob,
  formatDate,
  formatMoneyWithComma,
  formatFileSize,
  getProjectRoleLabel,
  getProjectStatusLabel,
  getTaskPriorityLabel,
  getCompetitionLevelLabel,
  getCompetitionStatusLabel,
  normalizePercentage,
} from '@/utils/format'

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

// ============================================
// formatDate
// ============================================
describe('formatDate', () => {
  it('returns "-" for null', () => {
    expect(formatDate(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatDate(undefined)).toBe('-')
  })

  it('returns "-" for empty string', () => {
    expect(formatDate('')).toBe('-')
  })

  it('formats an ISO date string as YYYY-MM-DD', () => {
    expect(formatDate('2024-01-15')).toBe('2024-01-15')
  })

  it('formats an ISO datetime string as YYYY-MM-DD (drops time)', () => {
    expect(formatDate('2024-06-15T10:30:00')).toBe('2024-06-15')
  })

  it('formats a Date object as YYYY-MM-DD', () => {
    expect(formatDate(new Date('2024-12-31'))).toBe('2024-12-31')
  })
})

// ============================================
// formatMoneyWithComma
// ============================================
describe('formatMoneyWithComma', () => {
  it('returns "¥0.00" for null', () => {
    expect(formatMoneyWithComma(null)).toBe('¥0.00')
  })

  it('returns "¥0.00" for undefined', () => {
    expect(formatMoneyWithComma(undefined)).toBe('¥0.00')
  })

  it('returns "¥0.00" for empty string', () => {
    expect(formatMoneyWithComma('')).toBe('¥0.00')
  })

  it('returns "¥0.00" for zero', () => {
    expect(formatMoneyWithComma(0)).toBe('¥0.00')
  })

  it('formats a number with thousands separator and 2 decimals', () => {
    expect(formatMoneyWithComma(1234.5)).toBe('¥1,234.50')
  })

  it('formats a large number with multiple thousands separators', () => {
    expect(formatMoneyWithComma(1234567.891)).toBe('¥1,234,567.89')
  })

  it('strips existing commas from string input before formatting', () => {
    expect(formatMoneyWithComma('1,234.5')).toBe('¥1,234.50')
  })

  it('strips the ¥ symbol from string input before formatting', () => {
    expect(formatMoneyWithComma('¥1000')).toBe('¥1,000.00')
  })

  it('falls back to "¥0.00" for a non-numeric string', () => {
    expect(formatMoneyWithComma('abc')).toBe('¥0.00')
  })
})

// ============================================
// formatFileSize
// ============================================
describe('formatFileSize', () => {
  it('returns "0 B" for zero', () => {
    expect(formatFileSize(0)).toBe('0 B')
  })

  it('returns "0 B" for null', () => {
    expect(formatFileSize(null)).toBe('0 B')
  })

  it('returns "0 B" for undefined', () => {
    expect(formatFileSize(undefined)).toBe('0 B')
  })

  it('formats bytes below 1 KB as B', () => {
    expect(formatFileSize(500)).toBe('500.00 B')
  })

  it('formats exactly 1024 bytes as 1.00 KB', () => {
    expect(formatFileSize(1024)).toBe('1.00 KB')
  })

  it('formats 1536 bytes as 1.50 KB', () => {
    expect(formatFileSize(1536)).toBe('1.50 KB')
  })

  it('formats exactly 1 MB', () => {
    expect(formatFileSize(1048576)).toBe('1.00 MB')
  })

  it('formats 1.5 MB', () => {
    expect(formatFileSize(1572864)).toBe('1.50 MB')
  })

  it('formats exactly 1 GB', () => {
    expect(formatFileSize(1073741824)).toBe('1.00 GB')
  })
})

describe('domain enum labels', () => {
  it('formats project status and member role values', () => {
    expect(getProjectStatusLabel('active')).toBe('进行中')
    expect(getProjectRoleLabel('leader')).toBe('项目负责人')
  })

  it('formats task priority values', () => {
    expect(getTaskPriorityLabel('urgent')).toBe('紧急')
  })

  it('formats current competition level and status values', () => {
    expect(getCompetitionLevelLabel('province')).toBe('省赛')
    expect(getCompetitionStatusLabel('preparing')).toBe('准备中')
  })
})

describe('normalizePercentage', () => {
  it('keeps backend percentages below one as percentage points', () => {
    expect(normalizePercentage(0.5)).toBe(0.5)
    expect(normalizePercentage(1)).toBe(1)
  })

  it('clamps values to a valid display range', () => {
    expect(normalizePercentage(-2)).toBe(0)
    expect(normalizePercentage(125)).toBe(100)
  })
})

describe('downloadBlob', () => {
  it('delays object URL cleanup until the browser has started the download', () => {
    vi.useFakeTimers()
    const blob = new Blob(['backup'], { type: 'application/zip' })
    const createObjectURL = vi.fn(() => 'blob:backup-download')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })

    downloadBlob(blob, 'team-backup.zip')

    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(click).toHaveBeenCalledOnce()
    expect(revokeObjectURL).not.toHaveBeenCalled()

    vi.advanceTimersByTime(999)
    expect(revokeObjectURL).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    expect(revokeObjectURL).toHaveBeenCalledOnce()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:backup-download')
  })
})
