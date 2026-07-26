import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PaginatedResponse, Task } from '@/types'

const { getMock, postMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: postMock,
  patch: vi.fn(),
  del: vi.fn(),
}))

import { changeTaskStatus, getTasksByProject } from '@/api/tasks'

function task(id: number): Task {
  return { id, title: `任务 ${id}` } as Task
}

function page(results: Task[], next: string | null): PaginatedResponse<Task> {
  return {
    count: 2,
    next,
    previous: null,
    results,
  }
}

beforeEach(() => {
  getMock.mockReset()
  postMock.mockReset()
})

describe('project task pagination', () => {
  it('loads every page for the project detail task board', async () => {
    getMock
      .mockResolvedValueOnce(page([task(1)], '/api/v1/tasks/?page=2'))
      .mockResolvedValueOnce(page([task(2)], null))

    await expect(getTasksByProject(7)).resolves.toEqual([task(1), task(2)])
    expect(getMock).toHaveBeenNthCalledWith(1, '/tasks/', {
      project: 7,
      page: 1,
      page_size: 100,
    })
    expect(getMock).toHaveBeenNthCalledWith(2, '/tasks/', {
      project: 7,
      page: 2,
      page_size: 100,
    })
  })

  it('keeps compatibility with an unpaginated response', async () => {
    getMock.mockResolvedValueOnce([task(1)])

    await expect(getTasksByProject(7)).resolves.toEqual([task(1)])
  })
})

describe('task status payload', () => {
  it('sends the delay reason and completion note through the governed action', async () => {
    postMock.mockResolvedValueOnce(task(9))

    await changeTaskStatus(9, 'pending_review', undefined, '交付物已上传')

    expect(postMock).toHaveBeenCalledWith('/tasks/9/change_status/', {
      to_status: 'pending_review',
      delay_reason: undefined,
      completion_note: '交付物已上传',
    })
  })
})
