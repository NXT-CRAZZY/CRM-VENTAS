import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Package, Plus } from 'lucide-react'
import { useState } from 'react'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { formatMoney } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { type Column, DataList } from '@/shared/ui/data-list'
import { EmptyState, ErrorState, NoResults } from '@/shared/ui/feedback'
import { PageContainer, PageHeader, Pagination, SearchInput, Segmented } from '@/shared/ui/page'
import {
  BILLING_LABEL,
  KIND_LABEL,
  type Product,
  type ProductFilters,
  productsKeys,
  productsService,
  useProductCategories,
} from '../api/products-service'
import { ProductFormSheet } from '../components/ProductFormSheet'

function PriceTag({ value }: { value: string }) {
  return Number(value) === 0 ? <Badge tone="success">Gratis</Badge> : <span className="tabular font-semibold text-zinc-900">{formatMoney(value)}</span>
}

export default function ProductsPage() {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const canManage = can(P.PRODUCTS_MANAGE)
  const categories = useProductCategories()
  const [search, setSearch] = useState('')
  const [categoryId, setCategoryId] = useState<string | undefined>()
  const [status, setStatus] = useState<ProductFilters['status']>('active')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Product | 'new' | null>(null)
  const q = useDebounce(search)

  const filters: ProductFilters = { q, category_id: categoryId, status, page }
  const products = useQuery({ queryKey: productsKeys.list(filters), queryFn: () => productsService.list(filters), placeholderData: keepPreviousData })
  const refresh = () => qc.invalidateQueries({ queryKey: productsKeys.all })
  const clear = () => {
    setSearch('')
    setCategoryId(undefined)
    setStatus('active')
    setPage(1)
  }

  const columns: Column<Product>[] = [
    { key: 'code', header: 'Código', className: 'w-36', cell: (p) => <code className="font-mono text-[13px] text-zinc-600">{p.code}</code> },
    {
      key: 'name',
      header: 'Producto',
      cell: (p) => (
        <div className="min-w-0">
          <p className={cn('font-medium text-zinc-900', !p.is_active && 'text-zinc-400 line-through')}>{p.name}</p>
          <p className="text-xs text-muted-foreground">{p.category.name}</p>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Tipo',
      cell: (p) => (
        <div className="flex flex-wrap gap-1">
          <Badge tone={p.kind === 'DEMO' ? 'info' : 'neutral'}>{KIND_LABEL[p.kind]}</Badge>
          {p.billing_period !== 'UNICO' && <Badge tone="brand">{BILLING_LABEL[p.billing_period]}</Badge>}
        </div>
      ),
    },
    { key: 'price', header: 'Precio', className: 'text-right', cell: (p) => <PriceTag value={p.list_price} /> },
  ]

  const chip = (active: boolean) =>
    cn(
      'inline-flex h-9 shrink-0 items-center gap-2 rounded-full border px-3.5 text-[13px] font-medium transition-all duration-150 sm:h-8',
      active ? 'border-ink-900 bg-ink-900 text-white shadow-sm' : 'border-zinc-200 bg-card text-zinc-600 hover:border-zinc-300 hover:text-zinc-900',
    )

  return (
    <PageContainer>
      <PageHeader
        title="Productos"
        description="Catálogo de productos y servicios de DATA SERVICE. Los precios son finales."
        actions={canManage && <Button onClick={() => setEditing('new')}><Plus /> Nuevo producto</Button>}
      />

      <div className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
        <button type="button" className={chip(!categoryId)} onClick={() => { setCategoryId(undefined); setPage(1) }}>
          Todas
        </button>
        {categories.data?.map((c) => (
          <button key={c.id} type="button" className={chip(categoryId === c.id)} onClick={() => { setCategoryId(c.id); setPage(1) }}>
            {c.name}
            <span className={cn('tabular text-xs', categoryId === c.id ? 'text-zinc-400' : 'text-zinc-400')}>{c.product_count}</span>
          </button>
        ))}
      </div>

      <Card>
        <div className="flex flex-col gap-3 border-b border-zinc-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Buscar por código o nombre" className="sm:max-w-xs sm:flex-1" />
          {canManage && (
            <Segmented
              value={status}
              onChange={(v) => { setStatus(v); setPage(1) }}
              options={[
                { value: 'active', label: 'Activos' },
                { value: 'inactive', label: 'Inactivos' },
                { value: 'all', label: 'Todos' },
              ]}
            />
          )}
        </div>
        {products.isError ? (
          <ErrorState error={products.error} onRetry={() => products.refetch()} />
        ) : (
          <DataList
            items={products.data?.items}
            loading={products.isPending}
            columns={columns}
            getKey={(p) => p.id}
            onItemClick={canManage ? setEditing : undefined}
            renderCard={(p) => (
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-[15px] font-medium leading-snug text-zinc-900">{p.name}</p>
                  <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    <code className="font-mono">{p.code}</code>·<span>{KIND_LABEL[p.kind]}</span>
                    {p.billing_period !== 'UNICO' && <>·<span>{BILLING_LABEL[p.billing_period]}</span></>}
                  </p>
                </div>
                <PriceTag value={p.list_price} />
              </div>
            )}
            empty={search || categoryId || status !== 'active' ? <NoResults onClear={clear} /> : <EmptyState icon={<Package />} title="Sin productos" />}
            footer={products.data && <Pagination page={page} pageSize={products.data.page_size} total={products.data.total} onPageChange={setPage} />}
          />
        )}
      </Card>

      {canManage && <ProductFormSheet product={editing} onClose={() => setEditing(null)} onSaved={refresh} />}
    </PageContainer>
  )
}
