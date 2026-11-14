import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '@/shared/ui/dialog'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { opportunitiesKeys } from '@/features/opportunities/api/opportunities-service'
import { tasksKeys } from '@/features/tasks/api/tasks-service'

import { quotesKeys, quotesService, type Quote } from '../api/quotes-service'

export const STATUS_LABEL: Record<string, string> = {
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

/** Una cotización enviada cuya fecha de vencimiento ya pasó. */
export function isExpired(q: Quote): boolean {
  if (q.status !== 'SENT' || !q.expiration_date) return false
  return new Date(`${q.expiration_date}T23:59:59`) < new Date()
}

export function QuoteStatusBadge({ quote }: { quote: Quote }) {
  return (
    <>
      <Badge tone={STATUS_TONE[quote.status]}>{STATUS_LABEL[quote.status]}</Badge>
      {isExpired(quote) && <Badge tone="danger">Vencida</Badge>}
    </>
  )
}

/** Detalle desplegable: productos en tabla alineada, total y estado. */
export function QuoteDetails({ quote }: { quote: Quote }) {
  const [open, setOpen] = useState(false)
  const n = quote.items.length
  const note = quoteStatusNote(quote)
  return (
    <div className="mt-1.5">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs font-medium text-zinc-600 hover:text-zinc-900"
      >
        <ChevronRight className={`size-3.5 transition-transform ${open ? 'rotate-90' : ''}`} />
        {n} producto{n !== 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 overflow-x-auto rounded-md bg-zinc-50 px-3 py-2 text-xs">
          <table className="w-full min-w-[360px] tabular-nums">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="pb-1 pr-3 font-medium">Producto</th>
                <th className="pb-1 pr-3 text-right font-medium">Cant.</th>
                <th className="pb-1 pr-3 text-right font-medium">Precio</th>
                <th className="pb-1 text-right font-medium">Subtotal</th>
              </tr>
            </thead>
            <tbody className="text-zinc-700">
              {quote.items.map((it) => (
                <tr key={it.id} className="border-t border-zinc-200/70 align-top">
                  <td className="py-1.5 pr-3 break-words">{it.description}</td>
                  <td className="py-1.5 pr-3 text-right">{it.quantity}</td>
                  <td className="py-1.5 pr-3 text-right">{formatMoney(Number(it.unit_price))}</td>
                  <td className="py-1.5 text-right font-medium text-zinc-900">{formatMoney(Number(it.total))}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-zinc-300 text-sm font-semibold text-zinc-900">
                <td colSpan={3} className="pt-1.5 pr-3 text-right">
                  Total
                </td>
                <td className="pt-1.5 text-right">{formatMoney(Number(quote.total))}</td>
              </tr>
            </tfoot>
          </table>
          {note && <p className="mt-2 text-muted-foreground">{note}</p>}
        </div>
      )}
    </div>
  )
}

/** Línea de detalle según el estado: cuándo se envió/aceptó/rechazó y por qué. */
export function quoteStatusNote(q: Quote): string | null {
  if (q.status === 'SENT' && q.sent_at) {
    const venc = q.expiration_date ? ` · vence ${formatDate(q.expiration_date)}` : ''
    return `Enviada el ${formatDate(q.sent_at)}${venc}`
  }
  if (q.status === 'ACCEPTED' && q.accepted_at) return `Aceptada el ${formatDate(q.accepted_at)}`
  if (q.status === 'REJECTED' && q.rejected_at) {
    return `Rechazada el ${formatDate(q.rejected_at)}${q.reject_reason ? ` · ${q.reject_reason.name}` : ''}`
  }
  return null
}

/** Botones de ciclo de vida (Enviar / Aceptar / Rechazar / Reabrir) con sus efectos. */
export function QuoteActions({ quote }: { quote: Quote }) {
  const queryClient = useQueryClient()
  const [rejectOpen, setRejectOpen] = useState(false)
  const [reasonId, setReasonId] = useState('')
  const [closeOpp, setCloseOpp] = useState(false)
  const [reasonError, setReasonError] = useState<string | null>(null)
  const catalogs = useCatalogBundle(['loss_reason'])

  const mutation = useMutation({
    mutationFn: (v: { status: Quote['status']; reject_reason_id?: string; close_opportunity?: boolean }) =>
      quotesService.changeStatus(quote.id, v),
    onSuccess: (_d, v) => {
      const hasOpp = !!quote.opportunity
      const msg: Record<string, string> = {
        SENT: 'Cotización enviada. Se creó una tarea de seguimiento.',
        ACCEPTED: hasOpp
          ? 'Cotización aceptada: el cliente quedó registrado y la oportunidad se cerró como ganada.'
          : 'Cotización aceptada: el cliente quedó registrado.',
        REJECTED: v.close_opportunity ? 'Cotización rechazada y oportunidad cerrada como perdida.' : 'Cotización rechazada.',
        DRAFT: 'Cotización reabierta como borrador.',
      }
      toast.success(msg[v.status] ?? 'Estado actualizado')
      queryClient.invalidateQueries({ queryKey: quotesKeys.all })
      queryClient.invalidateQueries({ queryKey: opportunitiesKeys.all })
      queryClient.invalidateQueries({ queryKey: tasksKeys.all })
      queryClient.invalidateQueries({ queryKey: ['prospects'] })
      setRejectOpen(false)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const confirmReject = () => {
    if (!reasonId) {
      setReasonError('Indica el motivo del rechazo')
      return
    }
    mutation.mutate({ status: 'REJECTED', reject_reason_id: reasonId, close_opportunity: closeOpp })
  }

  return (
    <>
      {quote.status === 'DRAFT' && (
        <Button size="sm" variant="outline" loading={mutation.isPending} onClick={() => mutation.mutate({ status: 'SENT' })}>
          Enviar
        </Button>
      )}
      {quote.status === 'SENT' && (
        <>
          <Button size="sm" loading={mutation.isPending} onClick={() => mutation.mutate({ status: 'ACCEPTED' })}>
            Aceptar
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-red-600"
            onClick={() => {
              setReasonId('')
              setCloseOpp(false)
              setReasonError(null)
              setRejectOpen(true)
            }}
          >
            Rechazar
          </Button>
        </>
      )}
      {(quote.status === 'SENT' || quote.status === 'REJECTED') && (
        <Button size="sm" variant="ghost" loading={mutation.isPending} onClick={() => mutation.mutate({ status: 'DRAFT' })}>
          Reabrir
        </Button>
      )}

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent className="max-w-md" hideClose>
          <DialogHeader
            title="Rechazar cotización"
            description="Indica por qué el cliente no la aceptó. Sirve para entender por qué se pierden ventas."
          />
          <FormField label="Motivo" required error={reasonError ?? undefined}>
            {(p) => (
              <Select
                {...p}
                value={reasonId}
                onValueChange={(v) => {
                  setReasonId(v)
                  setReasonError(null)
                }}
                options={(catalogs.data?.loss_reason ?? []).map((o) => ({ value: o.id, label: o.name }))}
                placeholder="Selecciona…"
              />
            )}
          </FormField>
          {quote.opportunity && (
            <label className="flex items-start gap-2 text-sm text-zinc-700">
              <input
                type="checkbox"
                className="mt-0.5 size-4 accent-brand-600"
                checked={closeOpp}
                onChange={(e) => setCloseOpp(e.target.checked)}
              />
              <span>
                Marcar también la oportunidad <span className="font-medium">{quote.opportunity.title}</span> como Cerrado perdido
                <span className="block text-xs text-muted-foreground">
                  Déjalo sin marcar si el cliente puede pedir otra cotización.
                </span>
              </span>
            </label>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectOpen(false)} disabled={mutation.isPending}>
              Cancelar
            </Button>
            <Button variant="destructive" loading={mutation.isPending} onClick={confirmReject}>
              Rechazar cotización
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
