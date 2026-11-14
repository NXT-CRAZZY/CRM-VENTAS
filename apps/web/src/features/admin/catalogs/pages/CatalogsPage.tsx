import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Lock, Plus } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { fadeUp, stagger } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Badge, ColorBadge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { DataListSkeleton } from '@/shared/ui/data-list'
import { EmptyState, ErrorState } from '@/shared/ui/feedback'
import { Select, Tooltip } from '@/shared/ui/menus'
import { PageContainer, PageHeader } from '@/shared/ui/page'
import { type CatalogOption, catalogsKeys, catalogsService } from '../api/catalogs-service'
import { OptionFormSheet } from '../components/OptionFormSheet'

export default function CatalogsPage() {
  const qc = useQueryClient()
  const catalogs = useQuery({ queryKey: catalogsKeys.list, queryFn: catalogsService.list })
  const [code, setCode] = useState<string | null>(null)
  const current = catalogs.data?.find((c) => c.code === code) ?? catalogs.data?.[0]
  const options = useQuery({
    queryKey: catalogsKeys.options(current?.code ?? ''),
    queryFn: () => catalogsService.options(current!.code),
    enabled: !!current,
  })
  const [editing, setEditing] = useState<CatalogOption | 'new' | null>(null)

  const refresh = () => qc.invalidateQueries({ queryKey: catalogsKeys.all })

  const reorder = useMutation({
    mutationFn: (ids: string[]) => catalogsService.reorder(current!.code, ids),
    onMutate: async (ids) => {
      // Reordenamiento optimista: la lista se mueve al instante.
      const key = catalogsKeys.options(current!.code)
      const prev = qc.getQueryData<CatalogOption[]>(key)
      qc.setQueryData<CatalogOption[]>(key, (old) => ids.map((id) => old!.find((o) => o.id === id)!))
      return { prev, key }
    },
    onError: (e, _ids, ctx) => {
      if (ctx) qc.setQueryData(ctx.key, ctx.prev)
      toast.error(errorMessage(e))
    },
    onSettled: refresh,
  })

  const move = (index: number, delta: number) => {
    const ids = options.data!.map((o) => o.id)
    const [item] = ids.splice(index, 1)
    ids.splice(index + delta, 0, item)
    reorder.mutate(ids)
  }

  if (catalogs.isError) return <PageContainer><ErrorState error={catalogs.error} onRetry={() => catalogs.refetch()} /></PageContainer>

  return (
    <PageContainer>
      <PageHeader title="Catálogos" description="Listas que usa el CRM en formularios, filtros y reportes. Ajústalas sin tocar código." />

      {catalogs.isPending ? (
        <Card><DataListSkeleton /></Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <div className="lg:hidden">
            <Select value={current?.code} onValueChange={setCode} options={catalogs.data.map((c) => ({ value: c.code, label: c.name }))} />
          </div>
          <nav className="hidden space-y-0.5 lg:block" aria-label="Catálogos">
            {catalogs.data.map((c) => {
              const active = c.code === current?.code
              return (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => setCode(c.code)}
                  className={cn(
                    'flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors',
                    active ? 'bg-card font-medium text-zinc-900 shadow-xs ring-1 ring-zinc-200/80' : 'text-zinc-600 hover:bg-card/70 hover:text-zinc-900',
                  )}
                >
                  {c.name}
                  <span className={cn('tabular text-xs', active ? 'text-brand-700' : 'text-zinc-400')}>{c.option_count}</span>
                </button>
              )
            })}
          </nav>

          {current && (
            <Card>
              <div className="flex flex-col gap-3 border-b border-zinc-100 p-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-base font-semibold text-zinc-900">{current.name}</h2>
                  {current.description && <p className="mt-0.5 text-sm text-muted-foreground">{current.description}</p>}
                </div>
                <Button size="sm" onClick={() => setEditing('new')}>
                  <Plus /> Agregar opción
                </Button>
              </div>

              {options.isPending ? (
                <DataListSkeleton rows={5} />
              ) : options.isError ? (
                <ErrorState error={options.error} onRetry={() => options.refetch()} />
              ) : options.data.length === 0 ? (
                <EmptyState title="Sin opciones" description="Agrega la primera opción de este catálogo." />
              ) : (
                <motion.ul key={current.code} variants={stagger} initial="hidden" animate="show" className="divide-y divide-zinc-100">
                  {options.data.map((o, i) => (
                    <motion.li key={o.id} layout variants={fadeUp} className={cn('flex items-center gap-3 px-4 py-3 sm:px-5', !o.is_active && 'opacity-55')}>
                      <div className="flex flex-col">
                        <button type="button" disabled={i === 0 || reorder.isPending} onClick={() => move(i, -1)} className="rounded p-0.5 text-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 disabled:invisible" aria-label="Subir">
                          <ArrowUp className="size-3.5" />
                        </button>
                        <button type="button" disabled={i === options.data.length - 1 || reorder.isPending} onClick={() => move(i, 1)} className="rounded p-0.5 text-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 disabled:invisible" aria-label="Bajar">
                          <ArrowDown className="size-3.5" />
                        </button>
                      </div>
                      <button type="button" onClick={() => setEditing(o)} className="flex min-w-0 flex-1 flex-col gap-1 rounded-md text-left sm:flex-row sm:items-center sm:gap-3">
                        <span className="min-w-0 sm:w-56">
                          {current.uses_color ? <ColorBadge color={o.color}>{o.name}</ColorBadge> : <span className="font-medium text-zinc-900">{o.name}</span>}
                        </span>
                        <span className="flex flex-wrap items-center gap-1.5 text-xs text-zinc-500">
                          <code className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[11px]">{o.code}</code>
                          {o.legacy_code && <Badge tone="info">Excel: {o.legacy_code}</Badge>}
                          {o.weight != null && <Badge>Peso {Number(o.weight)}</Badge>}
                          {!o.is_active && <Badge>Inactiva</Badge>}
                        </span>
                      </button>
                      {o.is_system && (
                        <Tooltip content="Opción del sistema">
                          <Lock className="size-3.5 shrink-0 text-zinc-300" />
                        </Tooltip>
                      )}
                    </motion.li>
                  ))}
                </motion.ul>
              )}
            </Card>
          )}
        </div>
      )}

      {current && <OptionFormSheet catalog={current} option={editing} onClose={() => setEditing(null)} onSaved={refresh} />}
    </PageContainer>
  )
}
