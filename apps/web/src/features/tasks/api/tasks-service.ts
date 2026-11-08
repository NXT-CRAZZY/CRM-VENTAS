import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Task = Schemas['TaskRead']
export type TaskCreate = Schemas['TaskCreate']
export type TaskUpdate = Schemas['TaskUpdate']

export const tasksKeys = {
  all: ['tasks'] as const,
  list: (filters: TaskFilters) => ['tasks', 'list', filters] as const,
}

export interface TaskFilters {
  status?: 'PENDING' | 'DONE' | 'CANCELLED'
  assignee_id?: string
  due_before?: string
  due_after?: string
  page?: number
}

export const tasksService = {
  list: (filters: TaskFilters = {}) =>
    unwrap(
      api.GET('/api/v1/tasks', {
        params: {
          query: {
            status: filters.status,
            assignee_id: filters.assignee_id,
            due_before: filters.due_before,
            due_after: filters.due_after,
            page: filters.page ?? 1,
            page_size: 100,
          },
        },
      }),
    ),
  create: (body: TaskCreate) => unwrap(api.POST('/api/v1/tasks', { body })),
  update: (id: string, body: TaskUpdate) =>
    unwrap(api.PATCH('/api/v1/tasks/{task_id}', { params: { path: { task_id: id } }, body })),
  changeStatus: (id: string, status: Task['status']) =>
    unwrap(api.PATCH('/api/v1/tasks/{task_id}/status', { params: { path: { task_id: id } }, body: { status } })),
  delete: (id: string) => unwrap(api.DELETE('/api/v1/tasks/{task_id}', { params: { path: { task_id: id } } })),
}
