import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronRight, History } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { api, type Schemas, unwrap } from '@/shared/api/client'
import { formatDateTime } from '@/shared/lib/format'
import { fadeUp, stagger } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Avatar } from '@/shared/ui/avatar'
import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { DataListSkeleton } from '@/shared/ui/data-list'
import { EmptyState, ErrorState, NoResults } from '@/shared/ui/feedback'
import { Input } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { PageContainer, PageHeader, Pagination } from '@/shared/ui/page'

type Log = Schemas['AuditLogRead']

const ACTION_LABEL: Record<string, string> = {
  'auth.login': 'Inició sesión',
  'auth.logout': 'Cerró sesión',
  'auth.locked': 'Cuenta bloqueada por intentos fallidos',
  'auth.refresh_reuse': 'Sesión cerrada por seguridad',
  'auth.password_changed': 'Cambió su contraseña',
  'user.created': 'Creó un usuario',
  'user.updated': 'Editó un usuario',
  'user.roles_changed': 'Cambió el rol de un usuario',
  'user.deactivated': 'Desactivó un usuario',
  'user.activated': 'Reactivó un usuario',
  'user.password_reset': 'Restableció una contraseña',
  'role.created': 'Creó un rol',
  'role.updated': 'Modificó un rol',
  'role.deleted': 'Eliminó un rol',
  'catalog_option.created': 'Agregó una opción de catálogo',
  'catalog_option.updated': 'Modificó una opción de catálogo',
  'product.created': 'Creó un producto',
  'product.updated': 'Editó un producto',
  'product.price_changed': 'Cambió el precio de un producto',
  'product_category.created': 'Creó una categoría de productos',
  'product_category.updated': 'Editó una categoría de productos',
  'settings.updated': 'Cambió la configuración',
}

const FILTERS = [
  { value: 'all', label: 'Todas las acciones' },
  { value: 'auth.', label: 'Accesos' },
  { value: 'user.', label: 'Usuarios' },
  { value: 'role.', label: 'Roles y permisos' },
  { value: 'catalog_option.', label: 'Catálogos' },
  { value: 'product', label: 'Productos' },
  { value: 'settings.', label: 'Configuración' },
]

const tone = (action: string) =>
  action.includes('deleted') || action.includes('deactivated') || action.includes('locked') || action.includes('reuse')
    ? 'danger'
    : action.includes('created')
      ? 'success'
      : action.startsWith('auth.')
        ? 'neutral'
        : 'info'

function fmt(v: unknown) {
  if (v === null || v === undefined || v === '') return '—'
  if (Array.isArray(v)) return v.join(', ') || '—'
  if (typeof v === 'boolean') return v ? 'Sí' : 'No'
  return String(v)
}

function Diff({ log }: { log: Log }) {
  const keys = [...new Set([...Object.keys(log.before ?? {}), ...Object.keys(log.after ?? {})])]
  if (!keys.length) return <p className="text-[13px] text-muted-foreground">Sin detalle de cambios.</p>
  return (
    <dl className="grid gap-2 text-[13px]">
      {keys.map((k) => (
        <div key={k} className="grid gap-1 sm:grid-cols-[160px_1fr]">
          <dt className="font-medium text-zinc-500">{k}</dt>
          <dd className="flex flex-wrap items-center gap-2">
            {log.before && k in log.before && <span className="rounded bg-red-50 px-1.5 py-0.5 text-red-800 line-through decoration-red-300">{fmt(log.before[k])}</span>}
            {log.after && k in log.after && <span className="rounded bg-green-50 px-1.5 py-0.5 text-green-800">{fmt(log.after[k])}</span>}
          </dd>
        </div>
      ))}
    </dl>
  )
}

export default function AuditPage() {
  const [action, setAction] = useState('all')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<number | null>(null)

  const logs = useQuery({
    queryKey: ['audit', action, from, to, page],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/audit-logs', {
          params: { query: { action: action === 'all' ? undefined : action, date_from: from || undefined, date_to: to || undefined, page, page_size: 25 } },
        }),
      ),
    placeholderData: keepPreviousData,
  })

  const filtered = action !== 'all' || from || to

  return (
    <PageContainer>
      <PageHeader title="Auditoría" description="Registro inalterable de las operaciones importantes: quién hizo qué y cuándo." />
      <Card>
        <div className="grid gap-3 border-b border-zinc-100 p-4 sm:grid-cols-[220px_160px_160px]">
          <Select value={action} onValueChange={(v) => { setAction(v); setPage(1) }} options={FILTERS} />
          <Input type="date" aria-label="Desde" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1) }} />
          <Input type="date" aria-label="Hasta" value={to} onChange={(e) => { setTo(e.target.value); setPage(1) }} />
        </div>
        {logs.isPending ? (
          <DataListSkeleton />
        ) : logs.isError ? (
          <ErrorState error={logs.error} onRetry={() => logs.refetch()} />
        ) : logs.data.items.length === 0 ? (
          filtered ? <NoResults onClear={() => { setAction('all'); setFrom(''); setTo('') }} /> : <EmptyState icon={<History />} title="Sin registros" />
        ) : (
          <>
            <motion.ul variants={stagger} initial="hidden" animate="show" className="divide-y divide-zinc-100">
              {logs.data.items.map((log) => {
                const expanded = open === log.id
                const hasDetail = !!(log.before || log.after)
                return (
                  <motion.li key={log.id} variants={fadeUp}>
                    <button
                      type="button"
                      disabled={!hasDetail}
                      onClick={() => setOpen(expanded ? null : log.id)}
                      className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-zinc-50/80 disabled:cursor-default disabled:hover:bg-transparent sm:px-5"
                    >
                      <Avatar name={log.user?.full_name ?? 'Sistema'} className="mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-zinc-900">
                          <span className="font-medium">{log.user?.full_name ?? 'Sistema'}</span>{' '}
                          <span className="text-zinc-600">{(ACTION_LABEL[log.action] ?? log.action).toLowerCase()}</span>
                          {log.entity_label && <span className="font-medium"> · {log.entity_label}</span>}
                        </p>
                        <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          {formatDateTime(log.created_at)}
                          <Badge tone={tone(log.action)}>{log.action}</Badge>
                          {log.ip && <span>IP {log.ip}</span>}
                        </p>
                      </div>
                      {hasDetail && <ChevronRight className={cn('mt-1 size-4 text-zinc-300 transition-transform duration-200', expanded && 'rotate-90')} />}
                    </button>
                    <AnimatePresence initial={false}>
                      {expanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="mx-4 mb-4 rounded-lg bg-zinc-50 p-4 sm:ml-16 sm:mr-5">
                            <Diff log={log} />
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.li>
                )
              })}
            </motion.ul>
            <Pagination page={page} pageSize={logs.data.page_size} total={logs.data.total} onPageChange={setPage} />
          </>
        )}
      </Card>
    </PageContainer>
  )
}
