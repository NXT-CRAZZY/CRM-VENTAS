import { useQuery } from '@tanstack/react-query'
import { api, type Schemas, unwrap } from '@/shared/api/client'

export type User = Schemas['UserRead']
export type UserCreate = Schemas['UserCreate']
export type UserUpdate = Schemas['UserUpdate']
export type UserStatusFilter = 'active' | 'inactive' | 'all'

export interface UserFilters {
  q?: string
  status: UserStatusFilter
  page: number
  page_size?: number
}

export const usersKeys = {
  all: ['users'] as const,
  list: (f: UserFilters) => ['users', 'list', f] as const,
}

export const usersService = {
  list: (f: UserFilters) =>
    unwrap(api.GET('/api/v1/users', { params: { query: { q: f.q || undefined, status: f.status, page: f.page, page_size: f.page_size ?? 20 } } })),
  create: (body: UserCreate) => unwrap(api.POST('/api/v1/users', { body })),
  update: (id: string, body: UserUpdate) => unwrap(api.PATCH('/api/v1/users/{user_id}', { params: { path: { user_id: id } }, body })),
  deactivate: (id: string) => unwrap(api.POST('/api/v1/users/{user_id}/deactivate', { params: { path: { user_id: id } } })),
  activate: (id: string) => unwrap(api.POST('/api/v1/users/{user_id}/activate', { params: { path: { user_id: id } } })),
  resetPassword: (id: string, password: string) =>
    unwrap(api.POST('/api/v1/users/{user_id}/reset-password', { params: { path: { user_id: id } }, body: { password } })),
}

export function useActiveUsers(enabled = true) {
  return useQuery({
    queryKey: usersKeys.list({ status: 'active', page: 1 }),
    queryFn: () => usersService.list({ status: 'active', page: 1, page_size: 100 }),
    select: (d) => d.items,
    staleTime: 2 * 60_000,
    enabled,
  })
}
