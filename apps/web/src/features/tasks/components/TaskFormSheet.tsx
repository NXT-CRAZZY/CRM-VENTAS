import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm, type Resolver } from 'react-hook-form'
import { useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { useActiveUsers } from '@/features/admin/users/api/users-service'
import { errorMessage } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'
import { Input, Textarea } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'

import { tasksKeys, tasksService, type Task } from '../api/tasks-service'
import { taskFormSchema, type TaskFormValues } from '../model/schemas'

function emptyToNull<T>(v: T): T | null {
  if (v === '' || v === undefined) return null
  return v
}

function fromISOString(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

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

  const catalogs = useCatalogBundle(['task_type', 'priority'])
  const users = useActiveUsers(true)

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
      queryClient.invalidateQueries({ queryKey: tasksKeys.all })
      onClose()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const selectOptions = (code: 'task_type' | 'priority') =>
    (catalogs.data?.[code] ?? []).map((o) => ({ value: o.id, label: o.name }))

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
          <FormField label="Título" required error={form.formState.errors.title?.message}>
            {(p) => <Input {...p} {...form.register('title')} />}
          </FormField>

          <FormField label="Descripción" optional error={form.formState.errors.description?.message}>
            {(p) => <Textarea {...p} rows={3} {...form.register('description')} />}
          </FormField>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Asignado a" optional error={form.formState.errors.assignee_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="assignee_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value ?? ''}
                      onValueChange={(v) => field.onChange(v || null)}
                      options={(users.data ?? []).map((u) => ({ value: u.id, label: u.full_name }))}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>

            <FormField label="Prioridad" optional error={form.formState.errors.priority_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="priority_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value ?? ''}
                      onValueChange={(v) => field.onChange(v || null)}
                      options={selectOptions('priority')}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
          </div>

          <FormField label="Tipo" optional error={form.formState.errors.type_id?.message}>
            {(p) => (
              <Controller
                control={form.control}
                name="type_id"
                render={({ field }) => (
                  <Select
                    {...p}
                    value={field.value ?? ''}
                    onValueChange={(v) => field.onChange(v || null)}
                    options={selectOptions('task_type')}
                    placeholder="—"
                  />
                )}
              />
            )}
          </FormField>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Vence el" optional error={form.formState.errors.due_at?.message}>
              {(p) => <Input {...p} type="datetime-local" {...form.register('due_at')} />}
            </FormField>

            <FormField label="Recordar el" optional error={form.formState.errors.remind_at?.message}>
              {(p) => <Input {...p} type="datetime-local" {...form.register('remind_at')} />}
            </FormField>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
