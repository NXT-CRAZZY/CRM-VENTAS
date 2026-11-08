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
            page: filters.page ?? 1,
            page_size: 100,
          },
        },
      }),
    ),
  create: (body: QuoteCreate) => unwrap(api.POST('/api/v1/quotes', { body })),
  update: (id: string, body: QuoteUpdate) =>
    unwrap(api.PATCH('/api/v1/quotes/{quote_id}', { params: { path: { quote_id: id } }, body })),
  changeStatus: (id: string, status: Quote['status']) =>
    unwrap(api.PATCH('/api/v1/quotes/{quote_id}/status', { params: { path: { quote_id: id } }, body: { status } })),
  delete: (id: string) => unwrap(api.DELETE('/api/v1/quotes/{quote_id}', { params: { path: { quote_id: id } } })),
}
