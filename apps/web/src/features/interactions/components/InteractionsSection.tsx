import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquarePlus, Pencil, Phone, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { type Schemas } from '@/shared/api/client'
import { errorMessage } from '@/shared/api/errors'
import { tasksKeys } from '@/features/tasks/api/tasks-service'
import { P, usePermissions } from '@/shared/auth/permissions'
import { formatDateTime } from '@/shared/lib/format'
import { Badge, ColorBadge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { ConfirmDialog } from '@/shared/ui/misc'

import { interactionsKeys, interactionsService, type Interaction } from '../api/interactions-service'
import { InteractionFormSheet } from './InteractionFormSheet'

export function InteractionsSection({
  prospectId,
  contacts,
  canUpdate,
}: {
  prospectId: string
  contacts: Schemas['ProspectContactRead'][]
  canUpdate: boolean
}) {
  const queryClient = useQueryClient()
  const { can } = usePermissions()
  const canCreate = can(P.INTERACTIONS_CREATE)

  const [formOpen, setFormOpen] = useState<Interaction | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Interaction | null>(null)

  const listQ = useQuery({
    queryKey: interactionsKeys.list(prospectId),
    queryFn: () => interactionsService.list(prospectId),
  })

  const deleteMutation = useMutation({
    mutationFn: (interaction: Interaction) => interactionsService.delete(prospectId, interaction.id),
    onSuccess: () => {
      toast.success('Interacción eliminada')
      queryClient.invalidateQueries({ queryKey: interactionsKeys.list(prospectId) })
      queryClient.invalidateQueries({ queryKey: ['prospects', 'detail', prospectId] })
      queryClient.invalidateQueries({ queryKey: tasksKeys.all })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setDeleting(null)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const interactions = listQ.data?.items ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Interacciones</h2>
        {canCreate && (
          <Button size="sm" onClick={() => setFormOpen('new')}>
            <MessageSquarePlus className="size-4" />
            Registrar
          </Button>
        )}
      </div>

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando interacciones…</p>
        ) : interactions.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <Phone className="mx-auto mb-2 size-8 text-zinc-300" />
            <p>Aún no hay interacciones registradas.</p>
            {canCreate && (
              <Button variant="outline" size="sm" className="mt-3" onClick={() => setFormOpen('new')}>
                Registrar la primera
              </Button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {interactions.map((i) => (
              <div key={i.id} className="p-4 text-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-zinc-900">Intento #{i.attempt_number}</span>
                      <Badge tone="neutral">{i.channel.name}</Badge>
                      {i.mode && <Badge tone="neutral">{i.mode.name}</Badge>}
                      <ColorBadge color={i.result.color}>{i.result.name}</ColorBadge>
                      {i.interest_level && <Badge tone="neutral">{i.interest_level.name}</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(i.occurred_at)}
                      {i.user && <> · {i.user.full_name}</>}
                      {i.contact && <> · {i.contact.full_name}</>}
                    </p>
                    {i.notes && <p className="mt-2 whitespace-pre-wrap text-zinc-700">{i.notes}</p>}
                    {i.opportunity && (
                      <p className="mt-2 text-xs text-zinc-500">
                        Oportunidad: <strong>{i.opportunity.title}</strong> · {i.opportunity.stage.name}
                      </p>
                    )}
                    {i.follow_up_task ? (
                      <p className="mt-2 text-xs text-brand-700">
                        Próxima acción: <strong>{i.follow_up_task.title}</strong>
                        {i.follow_up_task.due_at && <> · {formatDateTime(i.follow_up_task.due_at)}</>}
                        {i.follow_up_task.status !== 'PENDING' && <> · {i.follow_up_task.status === 'DONE' ? 'Hecha' : 'Cancelada'}</>}
                      </p>
                    ) : (
                      i.next_action_desc && (
                        <p className="mt-2 text-xs text-zinc-500">
                          Próxima acción (histórica): <strong>{i.next_action_desc}</strong>
                          {i.next_action_at && <> · {formatDateTime(i.next_action_at)}</>}
                        </p>
                      )
                    )}
                  </div>
                  {canUpdate && (
                    <div className="flex shrink-0 gap-1">
                      <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => setFormOpen(i)}>
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Eliminar"
                        className="text-red-600 hover:bg-red-50 hover:text-red-700"
                        onClick={() => setDeleting(i)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <InteractionFormSheet
        prospectId={prospectId}
        contacts={contacts.map((c) => ({ id: c.id, full_name: c.full_name }))}
        interaction={formOpen}
        onClose={() => setFormOpen(null)}
      />

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="¿Eliminar interacción?"
        description={`Se eliminará el intento #${deleting?.attempt_number}. Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={async () => {
          if (deleting) await deleteMutation.mutateAsync(deleting)
        }}
      />
    </div>
  )
}
