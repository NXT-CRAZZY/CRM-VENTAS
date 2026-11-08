import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, CheckCircle2, Clock, ListChecks, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDateTime } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { EmptyState } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { PageContainer, PageHeader, Segmented } from '@/shared/ui/page'

import { tasksKeys, tasksService, type Task } from '../api/tasks-service'
import { TaskFormSheet } from '../components/TaskFormSheet'

type Tab = 'today' | 'upcoming' | 'overdue' | 'done'

function isOverdue(task: Task): boolean {
  if (!task.due_at || task.status !== 'PENDING') return false
  return new Date(task.due_at) < new Date()
}

function TaskItem({
  task,
  onToggle,
  onEdit,
  onDelete,
}: {
  task: Task
  onToggle: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}) {
  const done = task.status === 'DONE'
  return (
    <div className="flex items-start gap-3 p-4 text-sm">
      <button
        className={cn(
          'mt-0.5 rounded-full border p-0.5 transition-colors',
          done
            ? 'border-green-500 bg-green-500 text-white'
            : 'border-zinc-300 text-zinc-400 hover:border-brand-500 hover:text-brand-600',
        )}
        onClick={() => onToggle(task)}
        aria-label={done ? 'Reabrir' : 'Completar'}
      >
        <Check className="size-3.5" />
      </button>
      <div className="flex-1">
        <p className={cn('font-medium text-zinc-900', done && 'text-zinc-500 line-through')}>{task.title}</p>
        {task.description && <p className={cn('mt-0.5', done ? 'text-zinc-400' : 'text-zinc-600')}>{task.description}</p>}
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
          {task.prospect && (
            <Link to={`/prospectos/${task.prospect.id}`} className="text-brand-700 hover:underline">
              {task.prospect.display_name}
            </Link>
          )}
          {task.type && <Badge tone="neutral">{task.type.name}</Badge>}
          {task.priority && <Badge tone="neutral">{task.priority.name}</Badge>}
          {task.due_at && (
            <span className={cn('text-muted-foreground', isOverdue(task) && !done && 'font-medium text-red-600')}>
              {formatDateTime(task.due_at)}
            </span>
          )}
          {task.assignee && <span className="text-muted-foreground">· {task.assignee.full_name}</span>}
        </div>
      </div>
      <div className="flex shrink-0 gap-1">
        <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => onEdit(task)}>
          <span className="text-xs font-medium">Editar</span>
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Eliminar"
          className="text-red-600 hover:bg-red-50 hover:text-red-700"
          onClick={() => onDelete(task)}
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
    </div>
  )
}

export default function TasksPage() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('today')
  const [editing, setEditing] = useState<Task | null>(null)
  const [deleting, setDeleting] = useState<Task | null>(null)

  const now = new Date()
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const endOfDay = new Date(startOfDay.getTime() + 24 * 60 * 60 * 1000)

  const filters =
    tab === 'today'
      ? { status: 'PENDING' as const, due_after: startOfDay.toISOString(), due_before: endOfDay.toISOString() }
      : tab === 'upcoming'
        ? { status: 'PENDING' as const, due_after: endOfDay.toISOString() }
        : tab === 'overdue'
          ? { status: 'PENDING' as const, due_before: startOfDay.toISOString() }
          : { status: 'DONE' as const }

  const listQ = useQuery({
    queryKey: tasksKeys.list(filters),
    queryFn: () => tasksService.list(filters),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Task['status'] }) => tasksService.changeStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tasksKeys.all }),
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: (task: Task) => tasksService.delete(task.id),
    onSuccess: () => {
      toast.success('Tarea eliminada')
      queryClient.invalidateQueries({ queryKey: tasksKeys.all })
      setDeleting(null)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const tasks = listQ.data?.items ?? []

  const emptyMessages: Record<Tab, { title: string; description: string; icon: React.ReactNode }> = {
    today: { title: 'Sin tareas para hoy', description: 'No tienes tareas programadas para hoy.', icon: <CheckCircle2 /> },
    upcoming: { title: 'Sin tareas próximas', description: 'No tienes tareas programadas a futuro.', icon: <ListChecks /> },
    overdue: { title: 'Sin tareas vencidas', description: 'Estás al día.', icon: <Clock /> },
    done: { title: 'Sin tareas completadas', description: 'Aún no has completado ninguna tarea.', icon: <CheckCircle2 /> },
  }

  const empty = emptyMessages[tab]

  return (
    <PageContainer>
      <PageHeader title="Tareas y recordatorios" description="Gestiona tus actividades de seguimiento." />

      <Segmented<Tab>
        value={tab}
        onChange={setTab}
        options={[
          { value: 'today', label: 'Hoy' },
          { value: 'upcoming', label: 'Próximas' },
          { value: 'overdue', label: 'Vencidas' },
          { value: 'done', label: 'Completadas' },
        ]}
        className="mb-6"
      />

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando tareas…</p>
        ) : tasks.length === 0 ? (
          <div className="p-8">
            <EmptyState icon={empty.icon} title={empty.title} description={empty.description} />
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {tasks.map((t) => (
              <TaskItem
                key={t.id}
                task={t}
                onToggle={(task) =>
                  statusMutation.mutate({ id: task.id, status: task.status === 'DONE' ? 'PENDING' : 'DONE' })
                }
                onEdit={setEditing}
                onDelete={setDeleting}
              />
            ))}
          </div>
        )}
      </Card>

      {editing && (
        <TaskFormSheet
          prospectId={editing.prospect?.id ?? ''}
          task={editing}
          onClose={() => setEditing(null)}
        />
      )}

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
    </PageContainer>
  )
}
