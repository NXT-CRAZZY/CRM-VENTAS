import { useQuery } from '@tanstack/react-query'
import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Role = Schemas['RoleRead']
export type PermissionGroup = Schemas['PermissionGroup']

export const rolesKeys = {
  roles: ['roles'] as const,
  permissions: ['permissions'] as const,
}

export const rolesService = {
  list: () => unwrap(api.GET('/api/v1/roles')),
  permissions: () => unwrap(api.GET('/api/v1/permissions')),
  create: (body: Schemas['RoleCreate']) => unwrap(api.POST('/api/v1/roles', { body })),
  update: (id: string, body: Schemas['RoleUpdate']) =>
    unwrap(api.PATCH('/api/v1/roles/{role_id}', { params: { path: { role_id: id } }, body })),
  remove: (id: string) => unwrap(api.DELETE('/api/v1/roles/{role_id}', { params: { path: { role_id: id } } })),
}

export const useRoles = () => useQuery({ queryKey: rolesKeys.roles, queryFn: rolesService.list })
export const usePermissionGroups = () =>
  useQuery({ queryKey: rolesKeys.permissions, queryFn: rolesService.permissions, staleTime: Infinity })
