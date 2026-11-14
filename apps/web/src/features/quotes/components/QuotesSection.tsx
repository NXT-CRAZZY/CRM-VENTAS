import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDate } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { ConfirmDialog } from '@/shared/ui/misc'

import { quotesKeys, quotesService, type Quote } from '../api/quotes-service'
import { QuoteActions, QuoteDetails, QuoteStatusBadge } from './QuoteActions'
import { QuoteFormSheet } from './QuoteFormSheet'

export function QuotesSection({ prospectId }: { prospectId: string }) {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState<Quote | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Quote | null>(null)

  const listQ = useQuery({
    queryKey: quotesKeys.list({ prospect_id: prospectId }),
    queryFn: () => quotesService.list({ prospect_id: prospectId }),
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
