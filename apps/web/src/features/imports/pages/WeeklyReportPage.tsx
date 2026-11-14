import { useQuery } from '@tanstack/react-query'
import { BarChart3, Calendar, ChevronRight, Download, Loader2, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { useActiveUsers } from '@/features/admin/users/api/users-service'
import { productsKeys, productsService } from '@/features/products/api/products-service'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { P, usePermissions } from '@/shared/auth/permissions'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Combobox } from '@/shared/ui/combobox'
import { Dialog, DialogContent, DialogHeader } from '@/shared/ui/dialog'
import { Input } from '@/shared/ui/input'
import { PageContainer, PageHeader } from '@/shared/ui/page'

import { importsKeys, importsService, type WeeklyFilters } from '../api/imports-service'

const iso = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Atajos que rellenan "Desde" y "Hasta". */
function shortcuts(): { id: string; label: string; from: string; to: string }[] {
  const now = new Date()
  const today = iso(now)
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((now.getDay() + 6) % 7))
  const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0)
  return [
    { id: 'today', label: 'Hoy', from: today, to: today },
    { id: 'week', label: 'Esta semana', from: iso(monday), to: today },
    { id: 'month', label: 'Este mes', from: iso(firstOfMonth), to: today },
    { id: 'lastmonth', label: 'Mes pasado', from: iso(lastMonthStart), to: iso(lastMonthEnd) },
  ]
}

export default function WeeklyReportPage() {
  const { can } = usePermissions()
  const canSeeAll = can(P.PROSPECTS_READ_ALL)

  // Fechas locales (no UTC). Por defecto: este mes.
  const [dateFrom, setDateFrom] = useState(() => shortcuts()[2]!.from)
  const [dateTo, setDateTo] = useState(() => shortcuts()[2]!.to)
  const [sellerId, setSellerId] = useState('all')
  const [productId, setProductId] = useState('all')
  const [typeId, setTypeId] = useState('all')
  const [detail, setDetail] = useState<{ key: string; label: string } | null>(null)

  const users = useActiveUsers(canSeeAll)
  const catalogs = useCatalogBundle(['opportunity_type'])
  const productsQ = useQuery({
    queryKey: productsKeys.list({ status: 'active', page: 1 }),
    queryFn: () => productsService.list({ status: 'active', page: 1 }),
  })

  const filters: WeeklyFilters = {
    date: dateTo || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    seller_id: sellerId === 'all' ? undefined : sellerId,
    product_id: productId === 'all' ? undefined : productId,
    type_id: typeId === 'all' ? undefined : typeId,
  }
  const hasFilters = !!(sellerId !== 'all' || productId !== 'all' || typeId !== 'all')
  const clearFilters = () => {
    setSellerId('all')
    setProductId('all')
    setTypeId('all')
  }

  const reportQuery = useQuery({
    queryKey: importsKeys.weeklyReport(filters),
    queryFn: () => importsService.weeklyReport(filters),
  })

  const [exporting, setExporting] = useState(false)
  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await importsService.exportWeeklyReport(filters)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `FOR-VEN-001_${dateFrom}_${dateTo}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.success('Excel descargado')
    } catch {
      toast.error('No se pudo descargar el Excel')
    } finally {
      setExporting(false)
    }
  }

  const report = reportQuery.data
  const periodRow = (key: string, kind: string) =>
    report?.rows.find((r) => r.key === key && r.kind === kind)?.range ?? 0
  const active = shortcuts().find((sc) => sc.from === dateFrom && sc.to === dateTo)?.id

  return (
    <PageContainer>
      <PageHeader
        title="Informe de ventas"
        description="Cotizaciones, ventas y nuevos clientes por periodo. El vendedor ve lo suyo; administración y gerencia ven todo."
        actions={
          <Button variant="outline" onClick={handleExport} disabled={exporting || reportQuery.isLoading}>
            {exporting ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Download className="mr-2 size-4" />}
            Descargar Excel
          </Button>
        }
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-wrap items-center gap-2 sm:col-span-2 lg:col-span-4">
          {shortcuts().map((sc) => (
            <Button
              key={sc.id}
              size="sm"
              variant={active === sc.id ? 'primary' : 'outline'}
              onClick={() => {
                setDateFrom(sc.from)
                setDateTo(sc.to)
              }}
            >
              {sc.label}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2 sm:col-span-2">
          <Calendar className="size-4 shrink-0 text-muted-foreground" />
          <Input type="date" value={dateFrom} max={dateTo || undefined} onChange={(e) => setDateFrom(e.target.value)} aria-label="Desde" />
          <span className="text-xs text-muted-foreground">a</span>
          <Input type="date" value={dateTo} min={dateFrom || undefined} onChange={(e) => setDateTo(e.target.value)} aria-label="Hasta" />
        </div>
        {canSeeAll && (
          <Combobox
            value={sellerId}
            onValueChange={setSellerId}
            placeholder="Vendedor"
            searchPlaceholder="Buscar vendedor…"
            options={[
              { value: 'all', label: 'Todo el equipo', searchText: 'todo equipo' },
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
        <Combobox
          value={typeId}
          onValueChange={setTypeId}
          placeholder="Tipo de venta"
          searchPlaceholder="Buscar tipo…"
          options={[
            { value: 'all', label: 'Todos los tipos', searchText: 'todos' },
            ...(catalogs.data?.opportunity_type ?? []).map((o) => ({ value: o.id, label: o.name, searchText: o.name })),
          ]}
        />
        {hasFilters && (
          <Button variant="ghost" size="sm" className="justify-self-start" onClick={clearFilters}>
            <X className="size-4" />
            Limpiar filtros
          </Button>
        )}
      </div>
      {(productId !== 'all' || typeId !== 'all') && (
        <p className="-mt-3 mb-4 text-xs text-muted-foreground">
          El producto y el tipo de venta no se aplican a "Nuevos clientes".
        </p>
      )}

      {reportQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando informe…</p>
      ) : report ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard label="Cotizaciones enviadas" value={periodRow('quotes', 'count')} />
            <MetricCard label="Ventas totales" value={formatMoney(Number(periodRow('sales', 'money')))} />
            <MetricCard label="Nuevos clientes" value={periodRow('clients', 'count')} />
          </div>

          <Card className="p-0">
            <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-2 text-xs text-muted-foreground">
              <span>Pulsa un indicador para ver qué lo compone.</span>
              {report.range_label && <span>Periodo: {report.range_label}</span>}
            </div>
            <table className="w-full text-sm">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="px-4 py-3 text-left">Indicador</th>
                  <th className="px-4 py-3 text-right">Total del periodo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {report.rows.map((row) => {
                  const sub = row.label.startsWith('   ')
                  return (
                    <tr
                      key={`${row.key}-${row.label}`}
                      className="cursor-pointer transition-colors hover:bg-zinc-50"
                      onClick={() => setDetail({ key: row.key, label: row.label.trim() })}
                    >
                      <td className={sub ? 'py-3 pl-9 pr-4 text-zinc-600' : 'px-4 py-3 font-medium text-zinc-900'}>
                        <span className="inline-flex items-center gap-1">
                          {row.label.trim()}
                          <ChevronRight className="size-3.5 text-zinc-300" />
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatValue(row.range ?? 0, row.kind)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No se pudo cargar el informe.</p>
      )}

      {detail && <DetailDialog filters={filters} detail={detail} onClose={() => setDetail(null)} />}
    </PageContainer>
  )
}

function DetailDialog({
  filters,
  detail,
  onClose,
}: {
  filters: WeeklyFilters
  detail: { key: string; label: string }
  onClose: () => void
}) {
  const q = useQuery({
    queryKey: importsKeys.weeklyDetail(filters, detail.key, 'range'),
    queryFn: () => importsService.weeklyDetail(filters, detail.key, 'range'),
  })
  const items = q.data ?? []
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader title={detail.label} description="Lo que compone este número en el periodo elegido." />
        {q.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : items.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No hay registros en este periodo.</p>
        ) : (
          <div className="max-h-[55vh] divide-y divide-zinc-100 overflow-y-auto rounded-md border border-zinc-200/70">
            {items.map((it) => (
              <div key={it.id} className="flex items-start gap-3 p-3 text-sm">
                <div className="min-w-0 flex-1">
                  <Link to={`/prospectos/${it.prospect_id}`} className="font-medium text-brand-700 hover:underline" onClick={onClose}>
                    {it.prospect_name}
                  </Link>
                  {it.description && <p className="break-words text-xs text-zinc-600">{it.description}</p>}
                  <p className="text-xs text-muted-foreground">
                    {[it.day ? formatDate(it.day) : null, it.status, it.seller].filter(Boolean).join(' · ')}
                  </p>
                </div>
                {it.amount != null && <span className="shrink-0 font-semibold tabular-nums">{formatMoney(it.amount)}</span>}
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <BarChart3 className="size-5 text-brand-600" />
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold text-zinc-900">{value}</p>
        </div>
      </div>
    </Card>
  )
}

function formatValue(value: number, kind: string) {
  return kind === 'money' ? formatMoney(value) : value
}
