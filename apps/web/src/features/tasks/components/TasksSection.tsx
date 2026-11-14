import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Circle, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDateTime } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { ConfirmDialog } from '@/shared/ui/misc'

import { invalidateTaskViews, tasksKeys, tasksService, type Task } from '../api/tasks-service'
import { TaskFormSheet } from './TaskFormSheet'

export function TasksSection({ prospectId }: { prospectId: string }) {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState<Task | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Task | null>(null)

  const listQ = useQuery({
    queryKey: tasksKeys.list({ prospect_id: prospectId }),
    queryFn: () => tasksService.list({ prospect_id: prospectId }),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Task['status'] }) =>
      tasksService.changeStatus(id, status),
    onSuccess: () => invalidateTaskViews(queryClient),
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: (task: Task) => tasksService.delete(task.id),
    onSuccess: () => {
      toast.success('Tarea eliminada')
      invalidateTaskViews(queryClient)
      setDeleting(null)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const tasks = listQ.data?.items ?? []
  const pending = tasks.filter((t) => t.status === 'PENDING')
  const done = tasks.filter((t) => t.status === 'DONE')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Tareas</h2>
        <Button size="sm" onClick={() => setFormOpen('new')}>
          <Plus className="size-4" />
          Nueva tarea
        </Button>
      </div>

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando tareas…</p>
        ) : tasks.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <Circle className="mx-auto mb-2 size-8 text-zinc-300" />
            <p>Aún no hay tareas para este prospecto.</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => setFormOpen('new')}>
              Crear la primera
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {pending.map((t) => (
              <div key={t.id} className="flex items-start gap-3 p-4 text-sm">
                <button
                  className="mt-0.5 rounded-full border border-zinc-300 p-0.5 text-zinc-400 hover:border-brand-500 hover:text-brand-600"
                  onClick={() => statusMutation.mutate({ id: t.id, status: 'DONE' })}
                  aria-label="Marcar como hecha"
                >
                  <Check className="size-3.5" />
                </button>
                <div className="flex-1">
                  <p className="font-medium text-zinc-900">{t.title}</p>
                  {t.description && <p className="mt-0.5 text-zinc-600">{t.description}</p>}
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    {t.type && <Badge tone="neutral">{t.type.name}</Badge>}
                    {t.priority && <Badge tone="neutral">{t.priority.name}</Badge>}
                    {t.due_at && <span>Vence: {formatDateTime(t.due_at)}</span>}
                    {t.assignee && <span>· {t.assignee.full_name}</span>}
                  </div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => setFormOpen(t)}>
                    <span className="text-xs font-medium">Editar</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Eliminar"
                    className="text-red-600 hover:bg-red-50 hover:text-red-700"
                    onClick={() => setDeleting(t)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
            ))}
            {done.length > 0 && (
              <div className="bg-zinc-50/60 p-3">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">Completadas</p>
                <div className="space-y-2">
                  {done.map((t) => (
                    <div key={t.id} className="flex items-start gap-2 text-sm text-zinc-500">
                      <Check className="mt-0.5 size-4 text-green-600" />
                      <span className="line-through">{t.title}</span>
                      <button
                        className="ml-auto text-zinc-400 hover:text-zinc-600"
                        onClick={() => statusMutation.mutate({ id: t.id, status: 'PENDING' })}
                        aria-label="Reabrir"
                      >
                        <X className="size-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      <TaskFormSheet prospectId={prospectId} task={formOpen} onClose={() => setFormOpen(null)} />

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="¿Eliminar tarea?"
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
