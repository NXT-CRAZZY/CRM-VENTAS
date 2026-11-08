import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KanbanSquare, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { ConfirmDialog } from '@/shared/ui/misc'

import { opportunitiesKeys, opportunitiesService, type Opportunity } from '../api/opportunities-service'
import { OpportunityFormSheet } from './OpportunityFormSheet'

export function OpportunitiesSection({ prospectId }: { prospectId: string }) {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState<Opportunity | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Opportunity | null>(null)

  const listQ = useQuery({
    queryKey: opportunitiesKeys.list({ prospect_id: prospectId }),
    queryFn: () => opportunitiesService.list({ prospect_id: prospectId }),
  })

  const deleteMutation = useMutation({
    mutationFn: (o: Opportunity) => opportunitiesService.delete(o.id),
    onSuccess: () => {
      toast.success('Oportunidad eliminada')
      queryClient.invalidateQueries({ queryKey: opportunitiesKeys.all })
      setDeleting(null)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const opportunities = listQ.data?.items ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Oportunidades</h2>
        <Button size="sm" onClick={() => setFormOpen('new')}>
          <Plus className="size-4" />
          Nueva oportunidad
        </Button>
      </div>

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando oportunidades…</p>
        ) : opportunities.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <KanbanSquare className="mx-auto mb-2 size-8 text-zinc-300" />
            <p>Aún no hay oportunidades para este prospecto.</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => setFormOpen('new')}>
              Crear la primera
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {opportunities.map((o) => (
              <div key={o.id} className="flex items-start gap-3 p-4 text-sm">
                <div className="mt-0.5 size-2 rounded-full" style={{ backgroundColor: o.stage.color ?? '#71717A' }} />
                <div className="flex-1">
                  <p className="font-medium text-zinc-900">{o.title}</p>
                  {o.description && <p className="mt-0.5 text-zinc-600">{o.description}</p>}
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge tone="neutral">{o.stage.name}</Badge>
                    {o.type && <Badge tone="neutral">{o.type.name}</Badge>}
                    {o.estimated_amount !== null && o.estimated_amount !== undefined && (
                      <span>{formatMoney(Number(o.estimated_amount))}</span>
                    )}
                    {o.probability !== null && o.probability !== undefined && <span>· {o.probability}%</span>}
                    {o.expected_close_date && <span>· Cierra: {formatDate(o.expected_close_date)}</span>}
                    {o.owner && <span>· {o.owner.full_name}</span>}
                  </div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => setFormOpen(o)}>
                    <span className="text-xs font-medium">Editar</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Eliminar"
                    className="text-red-600 hover:bg-red-50 hover:text-red-700"
                    onClick={() => setDeleting(o)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <OpportunityFormSheet prospectId={prospectId} opportunity={formOpen} onClose={() => setFormOpen(null)} />

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="¿Eliminar oportunidad?"
        description={`Se eliminará "${deleting?.title}". Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={async () => {
          if (deleting) await deleteMutation.mutateAsync(deleting)
        }}
      />
    </div>
  )
}
