import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, type Resolver } from 'react-hook-form'
import { useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'
import { emptyToNull, fromISOString } from '@/shared/lib/forms'
import { Sheet, SheetContent } from '@/shared/ui/sheet'

import { invalidateTaskViews, tasksService, type Task } from '../api/tasks-service'
import { taskFormSchema, type TaskFormValues } from '../model/schemas'
import { TaskFields } from './TaskFields'

export function TaskFormSheet({
  prospectId,
  task,
  onClose,
}: {
  prospectId: string
  task: Task | 'new' | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const isNew = task === 'new'
  const editing = task && task !== 'new' ? task : null

  const defaultValues: TaskFormValues = useMemo(
    () => ({
      title: editing?.title ?? '',
      description: editing?.description ?? '',
      assignee_id: editing?.assignee?.id ?? null,
      type_id: editing?.type?.id ?? null,
      priority_id: editing?.priority?.id ?? null,
      due_at: editing?.due_at ? fromISOString(editing.due_at) : '',
      remind_at: editing?.remind_at ? fromISOString(editing.remind_at) : '',
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [task],
  )

  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema) as Resolver<TaskFormValues>,
    defaultValues,
  })

  useEffect(() => {
    if (task) form.reset(defaultValues)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task, defaultValues])

  const save = useMutation({
    mutationFn: async (values: TaskFormValues) => {
      const base = {
        title: values.title,
        description: emptyToNull(values.description),
        assignee_id: emptyToNull(values.assignee_id),
        type_id: emptyToNull(values.type_id),
        priority_id: emptyToNull(values.priority_id),
        due_at: values.due_at ? new Date(values.due_at).toISOString() : null,
        remind_at: values.remind_at ? new Date(values.remind_at).toISOString() : null,
      }
      if (isNew) {
        return tasksService.create({ prospect_id: prospectId, ...base })
      }
      return tasksService.update(editing!.id, base)
    },
    onSuccess: () => {
      toast.success(isNew ? 'Tarea creada' : 'Tarea actualizada')
      invalidateTaskViews(queryClient)
      onClose()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
    <Sheet open={!!task} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={isNew ? 'Nueva tarea' : 'Editar tarea'}
        description={isNew ? 'Programa un seguimiento para este prospecto.' : editing?.title}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" form="task-form" loading={save.isPending}>
              {isNew ? 'Crear tarea' : 'Guardar cambios'}
            </Button>
          </>
        }
      >
        <form
          id="task-form"
          onSubmit={form.handleSubmit((d) => save.mutate(d))}
          className="space-y-5"
          noValidate
        >
          <TaskFields form={form} />
        </form>
      </SheetContent>
    </Sheet>
  )
}
