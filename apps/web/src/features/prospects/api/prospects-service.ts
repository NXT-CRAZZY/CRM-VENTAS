import { useQuery } from '@tanstack/react-query'
import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Prospect = Schemas['ProspectRead']
export type ProspectCreate = Schemas['ProspectCreate']
export type ProspectUpdate = Schemas['ProspectUpdate']
export type ProspectContact = Schemas['ProspectContactRead']
export type ProspectAssignment = Schemas['ProspectAssignmentRead']
export type ProspectStatusHistory = Schemas['ProspectStatusHistoryRead']
export type ProspectStatus = Schemas['ProspectStatus']
export type PersonType = Schemas['PersonType']
export type DuplicateCheckResult = Schemas['DuplicateCheckResult']
export type Tag = Schemas['TagRead']

export interface ProspectFilters {
  q?: string
  person_type?: PersonType
  status?: ProspectStatus
  relationship_type?: 'PROSPECTO' | 'CLIENTE'
  owner_id?: string
  interest_level_id?: string
  priority_id?: string
  source_id?: string
  page: number
}

export const prospectsKeys = {
  all: ['prospects'] as const,
  list: (f: ProspectFilters) => ['prospects', 'list', f] as const,
  detail: (id: string) => ['prospects', 'detail', id] as const,
  tags: ['prospects', 'tags'] as const,
}

export const prospectsService = {
  list: (f: ProspectFilters) =>
    unwrap(
      api.GET('/api/v1/prospects', {
        params: {
          query: {
            q: f.q || undefined,
            person_type: f.person_type,
            status: f.status,
            relationship_type: f.relationship_type,
            owner_id: f.owner_id,
            interest_level_id: f.interest_level_id,
            priority_id: f.priority_id,
            source_id: f.source_id,
            page: f.page,
            page_size: 25,
          },
        },
      }),
    ),
  get: (id: string) => unwrap(api.GET('/api/v1/prospects/{prospect_id}', { params: { path: { prospect_id: id } } })),
  getAssignments: (id: string) => unwrap(api.GET('/api/v1/prospects/{prospect_id}/assignments', { params: { path: { prospect_id: id } } })),
  getStatusHistory: (id: string) => unwrap(api.GET('/api/v1/prospects/{prospect_id}/status-history', { params: { path: { prospect_id: id } } })),
  create: (body: ProspectCreate) => unwrap(api.POST('/api/v1/prospects', { body })),
  update: (id: string, body: ProspectUpdate) =>
    unwrap(api.PATCH('/api/v1/prospects/{prospect_id}', { params: { path: { prospect_id: id } }, body })),
  delete: (id: string) => unwrap(api.DELETE('/api/v1/prospects/{prospect_id}', { params: { path: { prospect_id: id } } })),
  checkDuplicates: (body: Schemas['DuplicateCheckRequest']) =>
    unwrap(api.POST('/api/v1/prospects/duplicate-check', { body })),
  bulkAssign: (body: Schemas['BulkAssignRequest']) =>
    unwrap(api.POST('/api/v1/prospects/bulk-assign', { body })),
  assign: (id: string, body: Schemas['AssignRequest']) =>
    unwrap(api.POST('/api/v1/prospects/{prospect_id}/assign', { params: { path: { prospect_id: id } }, body })),
  changeStatus: (id: string, body: Schemas['StatusChangeRequest']) =>
    unwrap(api.POST('/api/v1/prospects/{prospect_id}/status', { params: { path: { prospect_id: id } }, body })),
  listTags: (): Promise<Tag[]> => unwrap(api.GET('/api/v1/tags')),
  createTag: (body: Schemas['TagCreate']) => unwrap(api.POST('/api/v1/tags', { body })),
}

export const useTags = () => useQuery<Tag[]>({ queryKey: prospectsKeys.tags, queryFn: prospectsService.listTags })
