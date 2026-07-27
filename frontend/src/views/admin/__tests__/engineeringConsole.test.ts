import { describe, expect, it } from 'vitest'
import type { EndpointItem } from '@/api/engineering'
import {
  filterEndpointOperations,
  flattenEndpointOperations,
  statusCodeTone,
} from '../engineeringConsole'

const endpoints: EndpointItem[] = [
  {
    path: '/api/v1/projects/{id}/',
    methods: ['GET', 'PATCH'],
    operations: {
      patch: {
        operation_id: 'projects_partial_update',
        summary: '更新项目详情',
        tags: ['项目', '写操作', '项目'],
      },
      get: {
        operation_id: 'projects_retrieve',
        summary: '查看项目详情',
        tags: ['项目'],
      },
    },
  },
  {
    path: '/api/v1/health/',
    methods: ['GET'],
    operations: {},
  },
]

describe('engineering console helpers', () => {
  it('flattens OpenAPI paths into sorted operation rows with metadata', () => {
    expect(flattenEndpointOperations(endpoints)).toEqual([
      {
        path: '/api/v1/health/',
        method: 'GET',
        operation_id: '',
        summary: '',
        tags: [],
      },
      {
        path: '/api/v1/projects/{id}/',
        method: 'GET',
        operation_id: 'projects_retrieve',
        summary: '查看项目详情',
        tags: ['项目'],
      },
      {
        path: '/api/v1/projects/{id}/',
        method: 'PATCH',
        operation_id: 'projects_partial_update',
        summary: '更新项目详情',
        tags: ['项目', '写操作'],
      },
    ])
  })

  it('searches operation summaries and tags case-insensitively', () => {
    const operations = flattenEndpointOperations(endpoints)

    expect(filterEndpointOperations(operations, '查看项目')).toEqual([
      expect.objectContaining({ operation_id: 'projects_retrieve' }),
    ])
    expect(filterEndpointOperations(operations, '  写操作  ')).toEqual([
      expect.objectContaining({ operation_id: 'projects_partial_update' }),
    ])
    expect(filterEndpointOperations(operations, 'PROJECTS_PARTIAL')).toEqual([
      expect.objectContaining({ operation_id: 'projects_partial_update' }),
    ])
  })

  it('maps HTTP status families to distinct tones', () => {
    expect(statusCodeTone('200')).toBe('success')
    expect(statusCodeTone('302')).toBe('info')
    expect(statusCodeTone('404')).toBe('warning')
    expect(statusCodeTone('503')).toBe('danger')
  })
})
