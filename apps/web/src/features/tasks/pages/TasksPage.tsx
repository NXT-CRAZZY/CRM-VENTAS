import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, CheckCircle2, Clock, ListChecks, Trash2, X } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { formatDateTime } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { EmptyState } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { Combobox } from '@/shared/ui/combobox'
import { Select } from '@/shared/ui/menus'
import { PageContainer, PageHeader, SearchInput, Segmented } from '@/shared/ui/page'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useActiveUsers } from '@/features/admin/users/api/users-service'

import { invalidateTaskViews, tasksKeys, tasksService, type Task, type TaskFilters } from '../api/tasks-service'
import { TaskFormSheet } from '../components/TaskFormSheet'
import { dayBounds, type TaskTab } from '../model/task-tabs'

type Tab = TaskTab

const SORT_OPTIONS = [
  { value: 'due_asc', label: 'Vencen primero' },
  { value: 'due_desc', label: 'Vencen al final' },
  { value: 'newest', label: 'Creadas recientemente' },
  { value: 'priority', label: 'Mayor prioridad' },
]

function isOverdue(task: Task): boolean {
  if (!task.due_at || task.status !== 'PENDING') return false
  return new Date(task.due_at) < new Date()
}

function TaskItem({
  task,
  onToggle,
  onEdit,
  onDelete,
  highlighted = false,
}: {
  task: Task
  highlighted?: boolean
  onToggle: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}) {
  const done = task.status === 'DONE'
  const ref = useRef<HTMLDivElement>(null)
  const reduceMotion = useReducedMotion()

  // Al llegar desde "Próximas acciones": centra la fila en pantalla.
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' })
  }, [highlighted, reduceMotion])

  return (
    <motion.div
      ref={ref}
      data-task-id={task.id}
      animate={highlighted && !reduceMotion ? { y: [0, -8, 0, -4, 0] } : { y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut', delay: 0.25 }}
      className={cn(
        'flex items-start gap-3 p-4 text-sm transition-colors duration-500',
        highlighted && 'bg-brand-50 ring-2 ring-inset ring-brand-500/60',
      )}
    >
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
    </motion.div>
  )
}

export default function TasksPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const dueParam = searchParams.get('due')
  const initialTab: Tab = dueParam === 'overdue' || dueParam === 'upcoming' ? dueParam : 'today'
  const [tab, setTab] = useState<Tab>(initialTab)
  // Tarea a resaltar (viene de "Próximas acciones" del inicio); se quita al hacer clic fuera de ella.
  const [highlightId, setHighlightId] = useState<string | null>(searchParams.get('task'))

  useEffect(() => {
    if (!highlightId) return
    const clear = (e: PointerEvent) => {
      if ((e.target as HTMLElement | null)?.closest(`[data-task-id="${highlightId}"]`)) return
      setHighlightId(null)
      setSearchParams({}, { replace: true })
    }
    document.addEventListener('pointerdown', clear)
    return () => document.removeEventListener('pointerdown', clear)
  }, [highlightId, setSearchParams])
  const [editing, setEditing] = useState<Task | null>(null)
  const [deleting, setDeleting] = useState<Task | null>(null)

  const { can } = usePermissions()
  const canSeeAll = can(P.PROSPECTS_READ_ALL)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<NonNullable<TaskFilters['sort']>>('due_asc')
  const [assigneeId, setAssigneeId] = useState(canSeeAll ? (searchParams.get('assignee') ?? 'all') : 'all')
  const [typeId, setTypeId] = useState('all')
  const [priorityId, setPriorityId] = useState('all')
  const debouncedSearch = useDebounce(search.trim(), 300)
  const users = useActiveUsers(canSeeAll)
  const catalogs = useCatalogBundle(['task_type', 'priority'])
  const hasFilters = !!(search || sort !== 'due_asc' || assigneeId !== 'all' || typeId !== 'all' || priorityId !== 'all')
  const clearFilters = () => {
    setSearch('')
    setSort('due_asc')
    setAssigneeId('all')
    setTypeId('all')
    setPriorityId('all')
  }

  const { start: startOfDay, end: endOfDay } = dayBounds()

  const baseFilters: TaskFilters =
    tab === 'today'
      ? { status: 'PENDING' as const, due_after: startOfDay.toISOString(), due_before: endOfDay.toISOString() }
      : tab === 'upcoming'
        ? { status: 'PENDING' as const, due_after: endOfDay.toISOString() }
        : tab === 'overdue'
          ? { status: 'PENDING' as const, due_before: startOfDay.toISOString() }
          : { status: 'DONE' as const }
  const filters: TaskFilters = {
    ...baseFilters,
    search: debouncedSearch || undefined,
    assignee_id: assigneeId === 'all' ? undefined : assigneeId,
    type_id: typeId === 'all' ? undefined : typeId,
    priority_id: priorityId === 'all' ? undefined : priorityId,
    sort,
  }

  const listQ = useQuery({
    queryKey: tasksKeys.list(filters),
    queryFn: () => tasksService.list(filters),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Task['status'] }) => tasksService.changeStatus(id, status),
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

  const emptyMessages: Record<Tab, { title: string; description: string; icon: React.ReactNode }> = {
    today: { title: 'Sin tareas para hoy', description: 'No tienes tareas programadas para hoy.', icon: <CheckCircle2 /> },
    upcoming: { title: 'Sin tareas próximas', description: 'No tienes tareas programadas a futuro.', icon: <ListChecks /> },
    overdue: { title: 'Sin tareas vencidas', description: 'Estás al día.', icon: <Clock /> },
    done: { title: 'Sin tareas completadas', description: 'Aún no has completado ninguna tarea.', icon: <CheckCircle2 /> },
  }

  const empty = emptyMessages[tab]

  return (
    <PageContainer>
      <PageHeader title="Tareas" description="Gestiona tus actividades de seguimiento." />

      <Segmented<Tab>
        value={tab}
        onChange={setTab}
        options={[
          { value: 'today', label: 'Hoy' },
          { value: 'upcoming', label: 'Próximas' },
          { value: 'overdue', label: 'Vencidas' },
          { value: 'done', label: 'Completadas' },
        ]}
        className="mb-4"
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar tarea o cliente…" className="lg:col-span-2" />
        <Select value={sort} onValueChange={(v) => setSort(v as NonNullable<TaskFilters['sort']>)} options={SORT_OPTIONS} />
        {canSeeAll && (
          <Combobox
            value={assigneeId}
            onValueChange={setAssigneeId}
            placeholder="Responsable"
            searchPlaceholder="Buscar responsable…"
            options={[
              { value: 'all', label: 'Todos los responsables', searchText: 'todos' },
              ...(users.data ?? []).map((u) => ({ value: u.id, label: u.full_name, searchText: u.full_name })),
            ]}
          />
        )}
        <Combobox
          value={typeId}
          onValueChange={setTypeId}
          placeholder="Tipo"
          searchPlaceholder="Buscar tipo…"
          options={[
            { value: 'all', label: 'Todos los tipos', searchText: 'todos' },
            ...(catalogs.data?.task_type ?? []).map((o) => ({ value: o.id, label: o.name, searchText: o.name })),
          ]}
        />
        <Combobox
          value={priorityId}
          onValueChange={setPriorityId}
          placeholder="Prioridad"
          searchPlaceholder="Buscar prioridad…"
          options={[
            { value: 'all', label: 'Todas las prioridades', searchText: 'todas' },
            ...(catalogs.data?.priority ?? []).map((o) => ({ value: o.id, label: o.name, searchText: o.name })),
          ]}
        />
        {hasFilters && (
          <Button variant="ghost" size="sm" className="justify-self-start" onClick={clearFilters}>
            <X className="size-4" />
            Limpiar filtros
          </Button>
        )}
      </div>

      <Card className="p-0">
        {listQ.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando tareas…</p>
        ) : tasks.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={empty.icon}
              title={hasFilters ? 'Sin resultados' : empty.title}
              description={hasFilters ? 'Ninguna tarea coincide con los filtros.' : empty.description}
            />
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {tasks.map((t) => (
              <TaskItem
                key={t.id}
                task={t}
                highlighted={t.id === highlightId}
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
