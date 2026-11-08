import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { EmptyState } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { PageContainer, PageHeader, Segmented } from '@/shared/ui/page'

import { quotesKeys, quotesService, type Quote } from '../api/quotes-service'
import { QuoteFormSheet } from '../components/QuoteFormSheet'

const STATUS_LABEL: Record<string, string> = {
  DRAFT: 'Borrador',
  SENT: 'Enviada',
  ACCEPTED: 'Aceptada',
  REJECTED: 'Rechazada',
}

const STATUS_TONE: Record<string, 'neutral' | 'brand' | 'success' | 'danger'> = {
  DRAFT: 'neutral',
  SENT: 'brand',
  ACCEPTED: 'success',
  REJECTED: 'danger',
}

type Tab = 'all' | 'DRAFT' | 'SENT' | 'ACCEPTED' | 'REJECTED'

export default function QuotesPage() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('all')
  const [formOpen, setFormOpen] = useState<Quote | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Quote | null>(null)

  const listQ = useQuery({
    queryKey: quotesKeys.list({ status: tab === 'all' ? undefined : tab }),
    queryFn: () => quotesService.list({ status: tab === 'all' ? undefined : tab }),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Quote['status'] }) => quotesService.changeStatus(id, status),
    onSuccess: () => {
      toast.success('Estado actualizado')
      queryClient.invalidateQueries({ queryKey: quotesKeys.all })
      queryClient.invalidateQueries({ queryKey: ['prospects'] })
    },
    onError: (e) => toast.error(errorMessage(e)),
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
        className="mb-6"
      />

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando cotizaciones…</p>
        ) : quotes.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<FileText />}
              title="Sin cotizaciones"
              description={tab === 'all' ? 'Aún no hay cotizaciones registradas.' : `No hay cotizaciones en estado ${STATUS_LABEL[tab]}.`}
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
                    <Badge tone={STATUS_TONE[q.status]}>{STATUS_LABEL[q.status]}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDate(q.issue_date)} · Total: {formatMoney(Number(q.total))} · {q.items.length} ítem{q.items.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-1">
                  {q.status === 'DRAFT' && (
                    <Button size="sm" variant="outline" onClick={() => statusMutation.mutate({ id: q.id, status: 'SENT' })}>
                      Enviar
                    </Button>
                  )}
                  {q.status === 'SENT' && (
                    <>
                      <Button size="sm" onClick={() => statusMutation.mutate({ id: q.id, status: 'ACCEPTED' })}>
                        Aceptar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600"
                        onClick={() => statusMutation.mutate({ id: q.id, status: 'REJECTED' })}
                      >
                        Rechazar
                      </Button>
                    </>
                  )}
                  <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => setFormOpen(q)}>
                    <span className="text-xs font-medium">Editar</span>
                  </Button>
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
