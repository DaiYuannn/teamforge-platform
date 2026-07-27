import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PaginatedResponse, Task } from '@/types'

const { getMock, postMock, patchMock, delMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
  delMock: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  get: getMock,
  post: postMock,
  patch: patchMock,
  del: delMock,
}))

import {
  changeTaskStatus,
  createTaskDependency,
  deleteTaskDependency,
  getSubTasks,
  getTaskComments,
  getTasksByProject,
  toggleSubTask,
  updateTaskComment,
} from '@/api/tasks'

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
  patchMock.mockReset()
  delMock.mockReset()
})

describe('task collaboration API contract', () => {
  it('scopes checklist and comments to the current task', async () => {
    getMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] })

    await getSubTasks({ parent: 42, page_size: 100, ordering: 'sort_order' })
    await getTaskComments({ task: 42, page_size: 100, ordering: 'created_at' })

    expect(getMock).toHaveBeenNthCalledWith(1, '/tasks/subtasks/', {
      parent: 42,
      page_size: 100,
      ordering: 'sort_order',
    })
    expect(getMock).toHaveBeenNthCalledWith(2, '/tasks/comments/', {
      task: 42,
      page_size: 100,
      ordering: 'created_at',
    })
  })

  it('uses governed action and resource endpoints', async () => {
    postMock.mockResolvedValue({})
    patchMock.mockResolvedValue({})
    delMock.mockResolvedValue(undefined)

    await toggleSubTask(5)
    await createTaskDependency({ task: 42, depends_on: 9 })
    await updateTaskComment(13, { content: '更新后的进展' })
    await deleteTaskDependency(8)

    expect(postMock).toHaveBeenNthCalledWith(1, '/tasks/subtasks/5/toggle/')
    expect(postMock).toHaveBeenNthCalledWith(2, '/tasks/dependencies/', {
      task: 42,
      depends_on: 9,
    })
    expect(patchMock).toHaveBeenCalledWith('/tasks/comments/13/', {
      content: '更新后的进展',
    })
    expect(delMock).toHaveBeenCalledWith('/tasks/dependencies/8/')
  })
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
