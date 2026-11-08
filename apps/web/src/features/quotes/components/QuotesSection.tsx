import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { ConfirmDialog } from '@/shared/ui/misc'

import { quotesKeys, quotesService, type Quote } from '../api/quotes-service'
import { QuoteFormSheet } from './QuoteFormSheet'

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

export function QuotesSection({ prospectId }: { prospectId: string }) {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState<Quote | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Quote | null>(null)

  const listQ = useQuery({
    queryKey: quotesKeys.list({ prospect_id: prospectId }),
    queryFn: () => quotesService.list({ prospect_id: prospectId }),
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Cotizaciones</h2>
        <Button size="sm" onClick={() => setFormOpen('new')}>
          <Plus className="size-4" />
          Nueva cotización
        </Button>
      </div>

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando cotizaciones…</p>
        ) : quotes.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <FileText className="mx-auto mb-2 size-8 text-zinc-300" />
            <p>Aún no hay cotizaciones para este prospecto.</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => setFormOpen('new')}>
              Crear la primera
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {quotes.map((q) => (
              <div key={q.id} className="flex items-start gap-3 p-4 text-sm">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={STATUS_TONE[q.status]}>{STATUS_LABEL[q.status]}</Badge>
                    <span className="text-xs text-muted-foreground">{formatDate(q.issue_date)}</span>
                  </div>
                  <p className="mt-1 font-medium text-zinc-900">Total: {formatMoney(Number(q.total))}</p>
                  <p className="text-xs text-muted-foreground">{q.items.length} ítem{q.items.length !== 1 ? 's' : ''}</p>
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

      <QuoteFormSheet prospectId={prospectId} quote={formOpen} onClose={() => setFormOpen(null)} />

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
    </div>
  )
}
