import { describe, it, expect } from 'vitest'
import {
  formatDate,
  formatMoneyWithComma,
  formatFileSize,
} from '@/utils/format'

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
