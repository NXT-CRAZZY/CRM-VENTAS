import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Opportunity = Schemas['OpportunityRead']
export type OpportunityCreate = Schemas['OpportunityCreate']
export type OpportunityUpdate = Schemas['OpportunityUpdate']

export const opportunitiesKeys = {
  all: ['opportunities'] as const,
  list: (filters: OpportunityFilters) => ['opportunities', 'list', filters] as const,
}

export interface OpportunityFilters {
  stage_id?: string
  owner_id?: string
  type_id?: string
  prospect_id?: string
  expected_close_before?: string
  expected_close_after?: string
  page?: number
}

export const opportunitiesService = {
  list: (filters: OpportunityFilters = {}) =>
    unwrap(
      api.GET('/api/v1/opportunities', {
        params: {
          query: {
            stage_id: filters.stage_id,
            owner_id: filters.owner_id,
            type_id: filters.type_id,
            prospect_id: filters.prospect_id,
            expected_close_before: filters.expected_close_before,
            expected_close_after: filters.expected_close_after,
            page: filters.page ?? 1,
            page_size: 100,
          },
        },
      }),
    ),
  create: (body: OpportunityCreate) => unwrap(api.POST('/api/v1/opportunities', { body })),
  update: (id: string, body: OpportunityUpdate) =>
    unwrap(api.PATCH('/api/v1/opportunities/{opportunity_id}', { params: { path: { opportunity_id: id } }, body })),
  delete: (id: string) =>
    unwrap(api.DELETE('/api/v1/opportunities/{opportunity_id}', { params: { path: { opportunity_id: id } } })),
}
