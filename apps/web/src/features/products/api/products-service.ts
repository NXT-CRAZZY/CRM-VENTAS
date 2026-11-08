import { useQuery } from '@tanstack/react-query'
import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Product = Schemas['ProductRead']
export type ProductCategory = Schemas['CategoryRead']
export type ProductKind = Schemas['ProductKind']
export type BillingPeriod = Schemas['BillingPeriod']

export const KIND_LABEL: Record<ProductKind, string> = {
  LICENCIA_PERPETUA: 'Licencia',
  SUSCRIPCION: 'Suscripción',
  USUARIO_ADICIONAL: 'Usuario adicional',
  DEMO: 'Demo',
}

export const BILLING_LABEL: Record<BillingPeriod, string> = {
  UNICO: 'Pago único',
  SEMANAL: 'Semanal',
  MENSUAL: 'Mensual',
  ANUAL: 'Anual',
}

export interface ProductFilters {
  q?: string
  category_id?: string
  status: 'active' | 'inactive' | 'all'
  page: number
}

export const productsKeys = {
  all: ['products'] as const,
  list: (f: ProductFilters) => ['products', 'list', f] as const,
  categories: ['products', 'categories'] as const,
}

export const productsService = {
  list: (f: ProductFilters) =>
    unwrap(
      api.GET('/api/v1/products', {
        params: { query: { q: f.q || undefined, category_id: f.category_id, status: f.status, page: f.page, page_size: 50 } },
      }),
    ),
  categories: () => unwrap(api.GET('/api/v1/product-categories')),
  create: (body: Schemas['ProductCreate']) => unwrap(api.POST('/api/v1/products', { body })),
  update: (id: string, body: Schemas['ProductUpdate']) =>
    unwrap(api.PATCH('/api/v1/products/{product_id}', { params: { path: { product_id: id } }, body })),
}

export const useProductCategories = () => useQuery({ queryKey: productsKeys.categories, queryFn: productsService.categories })
