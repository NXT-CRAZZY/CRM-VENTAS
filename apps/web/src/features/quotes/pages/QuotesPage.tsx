import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDate } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { EmptyState } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { Combobox } from '@/shared/ui/combobox'
import { Input } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { PageContainer, PageHeader, SearchInput, Segmented } from '@/shared/ui/page'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useActiveUsers } from '@/features/admin/users/api/users-service'
import { productsKeys, productsService } from '@/features/products/api/products-service'

import { quotesKeys, quotesService, type Quote, type QuoteFilters } from '../api/quotes-service'
import { QuoteActions, QuoteDetails, QuoteStatusBadge, STATUS_LABEL } from '../components/QuoteActions'
import { QuoteFormSheet } from '../components/QuoteFormSheet'

type Tab = 'all' | 'DRAFT' | 'SENT' | 'ACCEPTED' | 'REJECTED'

const SORT_OPTIONS = [
  { value: 'newest', label: 'Más recientes' },
  { value: 'oldest', label: 'Más antiguas' },
  { value: 'amount_desc', label: 'Mayor monto' },
  { value: 'amount_asc', label: 'Menor monto' },
  { value: 'expiring', label: 'Por vencer primero (enviadas)' },
]

export default function QuotesPage() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('all')
  const [formOpen, setFormOpen] = useState<Quote | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Quote | null>(null)

  const { can } = usePermissions()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<NonNullable<QuoteFilters['sort']>>('newest')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [ownerId, setOwnerId] = useState('all')
  const [productId, setProductId] = useState('all')
  const debouncedSearch = useDebounce(search.trim(), 300)
  const canSeeAll = can(P.PROSPECTS_READ_ALL)

  const users = useActiveUsers(canSeeAll)
  const productsQ = useQuery({
    queryKey: productsKeys.list({ status: 'active', page: 1 }),
    queryFn: () => productsService.list({ status: 'active', page: 1 }),
  })

  const filters: QuoteFilters = {
    status: tab === 'all' ? undefined : tab,
    search: debouncedSearch || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    owner_id: ownerId === 'all' ? undefined : ownerId,
    product_id: productId === 'all' ? undefined : productId,
    sort,
  }
  const hasFilters = !!(search || dateFrom || dateTo || ownerId !== 'all' || productId !== 'all' || sort !== 'newest')
  const clearFilters = () => {
    setSearch('')
    setSort('newest')
    setDateFrom('')
    setDateTo('')
    setOwnerId('all')
    setProductId('all')
  }

  const listQ = useQuery({
    queryKey: quotesKeys.list(filters),
    queryFn: () => quotesService.list(filters),
  })

  const deleteMutation = useMutation({
    mutationFn: (q: Quote) => quotesService.delete(q.id),
    onSuccess: () => {
      toast.success('Cotización eliminada')
      queryClient.invalidateQueries({ queryKey: quotesKeys.all })
      setDeleting(null)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const quotes = listQ.data?.items ?? []

  return (
    <PageContainer>
      <PageHeader
        title="Cotizaciones"
        description="Gestiona propuestas comerciales y su estado."
        actions={
          <Button onClick={() => setFormOpen('new')}>
            <Plus className="size-4" />
            Nueva cotización
          </Button>
        }
      />

      <Segmented<Tab>
        value={tab}
        onChange={setTab}
        options={[
          { value: 'all', label: 'Todas' },
          { value: 'DRAFT', label: 'Borrador' },
          { value: 'SENT', label: 'Enviadas' },
          { value: 'ACCEPTED', label: 'Aceptadas' },
          { value: 'REJECTED', label: 'Rechazadas' },
        ]}
        className="mb-4"
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar cliente o documento…" className="lg:col-span-2" />
        <Select
          value={sort}
          onValueChange={(v) => setSort(v as NonNullable<QuoteFilters['sort']>)}
          options={SORT_OPTIONS}
        />
        {canSeeAll && (
          <Combobox
            value={ownerId}
            onValueChange={setOwnerId}
            placeholder="Responsable"
            searchPlaceholder="Buscar responsable…"
            options={[
              { value: 'all', label: 'Todos los responsables', searchText: 'todos' },
              ...(users.data ?? []).map((u) => ({ value: u.id, label: u.full_name, searchText: u.full_name })),
            ]}
          />
        )}
        <Combobox
          value={productId}
          onValueChange={setProductId}
          placeholder="Producto"
          searchPlaceholder="Buscar producto…"
          options={[
            { value: 'all', label: 'Todos los productos', searchText: 'todos' },
            ...(productsQ.data?.items ?? []).map((pr) => ({ value: pr.id, label: pr.name, searchText: `${pr.name} ${pr.code}` })),
          ]}
        />
        <div className="flex items-center gap-2 sm:col-span-2">
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="Emitidas desde" />
          <span className="text-xs text-muted-foreground">a</span>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="Emitidas hasta" />
        </div>
        {hasFilters && (
          <Button variant="ghost" size="sm" className="justify-self-start" onClick={clearFilters}>
            <X className="size-4" />
            Limpiar filtros
          </Button>
        )}
      </div>

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando cotizaciones…</p>
        ) : quotes.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<FileText />}
              title="Sin cotizaciones"
              description={hasFilters ? 'Ninguna cotización coincide con los filtros.' : tab === 'all' ? 'Aún no hay cotizaciones registradas.' : `No hay cotizaciones en estado ${STATUS_LABEL[tab]}.`}
            />
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {quotes.map((q) => (
              <div key={q.id} className="flex items-start gap-3 p-4 text-sm">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={`/prospectos/${q.prospect.id}`} className="font-medium text-brand-700 hover:underline">
                      {q.prospect.display_name}
                    </Link>
                    <QuoteStatusBadge quote={q} />
                    <span className="text-xs text-muted-foreground">{formatDate(q.issue_date)}</span>
                  </div>
                  <QuoteDetails quote={q} />
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-1">
                  <QuoteActions quote={q} />
                  {q.status === 'DRAFT' && (
                    <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => setFormOpen(q)}>
                      <span className="text-xs font-medium">Editar</span>
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Eliminar"
                    className="text-red-600 hover:bg-red-50 hover:text-red-700"
                    onClick={() => setDeleting(q)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {formOpen && formOpen !== 'new' && (
        <QuoteFormSheet prospectId={formOpen.prospect.id} quote={formOpen} onClose={() => setFormOpen(null)} />
      )}
      {formOpen === 'new' && (
        <QuoteFormSheet prospectId="" quote="new" onClose={() => setFormOpen(null)} />
      )}

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="¿Eliminar cotización?"
        description="Se eliminará la cotización. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        destructive
        onConfirm={async () => {
          if (deleting) await deleteMutation.mutateAsync(deleting)
        }}
      />
    </PageContainer>
  )
}
