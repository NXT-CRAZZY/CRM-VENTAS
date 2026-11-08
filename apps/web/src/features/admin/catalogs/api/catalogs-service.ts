import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Catalog = Schemas['CatalogRead']
export type CatalogOption = Schemas['CatalogOptionRead']

export const catalogsKeys = {
  all: ['catalogs'] as const,
  list: ['catalogs', 'list'] as const,
  options: (code: string) => ['catalogs', 'options', code] as const,
}

export const catalogsService = {
  list: () => unwrap(api.GET('/api/v1/catalogs')),
  options: (code: string) =>
    unwrap(api.GET('/api/v1/catalogs/{code}/options', { params: { path: { code }, query: { include_inactive: true } } })),
  create: (code: string, body: Schemas['CatalogOptionCreate']) =>
    unwrap(api.POST('/api/v1/catalogs/{code}/options', { params: { path: { code } }, body })),
  update: (id: string, body: Schemas['CatalogOptionUpdate']) =>
    unwrap(api.PATCH('/api/v1/catalog-options/{option_id}', { params: { path: { option_id: id } }, body })),
  reorder: (code: string, option_ids: string[]) =>
    unwrap(api.PUT('/api/v1/catalogs/{code}/order', { params: { path: { code } }, body: { option_ids } })),
}
