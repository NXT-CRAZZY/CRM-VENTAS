import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Quote = Schemas['QuoteRead']
export type QuoteCreate = Schemas['QuoteCreate']
export type QuoteUpdate = Schemas['QuoteUpdate']

export const quotesKeys = {
  all: ['quotes'] as const,
  list: (filters: QuoteFilters) => ['quotes', 'list', filters] as const,
}

export interface QuoteFilters {
  status?: 'DRAFT' | 'SENT' | 'ACCEPTED' | 'REJECTED'
  prospect_id?: string
  opportunity_id?: string
  search?: string
  date_from?: string
  date_to?: string
  owner_id?: string
  product_id?: string
  sort?: 'newest' | 'oldest' | 'amount_desc' | 'amount_asc' | 'expiring'
  page?: number
}

export const quotesService = {
  list: (filters: QuoteFilters = {}) =>
    unwrap(
      api.GET('/api/v1/quotes', {
        params: {
          query: {
            status: filters.status,
            prospect_id: filters.prospect_id,
            opportunity_id: filters.opportunity_id,
            search: filters.search || undefined,
            date_from: filters.date_from || undefined,
            date_to: filters.date_to || undefined,
            owner_id: filters.owner_id,
            product_id: filters.product_id,
            sort: filters.sort,
            page: filters.page ?? 1,
            page_size: 100,
          },
        },
      }),
    ),
  create: (body: QuoteCreate) => unwrap(api.POST('/api/v1/quotes', { body })),
  update: (id: string, body: QuoteUpdate) =>
    unwrap(api.PATCH('/api/v1/quotes/{quote_id}', { params: { path: { quote_id: id } }, body })),
  changeStatus: (
    id: string,
    body: { status: Quote['status']; reject_reason_id?: string; close_opportunity?: boolean },
  ) =>
    unwrap(api.PATCH('/api/v1/quotes/{quote_id}/status', { params: { path: { quote_id: id } }, body: { ...body, close_opportunity: body.close_opportunity ?? false } })),
  delete: (id: string) => unwrap(api.DELETE('/api/v1/quotes/{quote_id}', { params: { path: { quote_id: id } } })),
}
