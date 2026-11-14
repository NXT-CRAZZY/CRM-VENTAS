import { Controller, get, type UseFormReturn } from 'react-hook-form'
import { useActiveUsers } from '@/features/admin/users/api/users-service'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { P, usePermissions } from '@/shared/auth/permissions'
import { Input, Textarea } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'

/**
 * Campos de una tarea. Los usan el formulario de Tareas y la "próxima acción" de una interacción,
 * para que ambos pidan exactamente lo mismo. `prefix` es la ruta del objeto tarea dentro del formulario
 * (p. ej. "follow_up_task"); sin prefijo, los campos están en la raíz.
 */
export function TaskFields({
  form,
  prefix,
  children,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  form: UseFormReturn<any>
  prefix?: string
  /** Contenido extra (p. ej. atajos de fecha) tras "Vence el" / "Recordar el". */
  children?: React.ReactNode
}) {
  const { can } = usePermissions()
  const catalogs = useCatalogBundle(['task_type', 'priority'])
  // Solo quien puede leer usuarios puede elegir responsable; el resto queda asignado a sí mismo.
  const canPickAssignee = can(P.USERS_READ)
  const users = useActiveUsers(canPickAssignee)

  const name = (key: string) => (prefix ? `${prefix}.${key}` : key)
  const error = (key: string) => (get(form.formState.errors, name(key)) as { message?: string } | undefined)?.message
  const options = (code: 'task_type' | 'priority') =>
    (catalogs.data?.[code] ?? []).map((o) => ({ value: o.id, label: o.name }))

  const selectField = (key: string, label: string, opts: { value: string; label: string }[]) => (
    <FormField label={label} optional error={error(key)}>
      {(p) => (
        <Controller
          control={form.control}
          name={name(key)}
          render={({ field }) => (
            <Select
              {...p}
              value={field.value ?? ''}
              onValueChange={(v) => field.onChange(v || null)}
              options={opts}
              placeholder="—"
            />
          )}
        />
      )}
    </FormField>
  )

  return (
    <>
      <FormField label="Título" required error={error('title')}>
        {(p) => <Input {...p} {...form.register(name('title'))} placeholder="Ej: Enviar cotización" />}
      </FormField>

      <FormField label="Descripción" optional error={error('description')}>
        {(p) => <Textarea {...p} rows={3} {...form.register(name('description'))} />}
      </FormField>

      <div className="grid gap-5 sm:grid-cols-2">
        {canPickAssignee &&
          selectField(
            'assignee_id',
            'Asignado a',
            (users.data ?? []).map((u) => ({ value: u.id, label: u.full_name })),
          )}
        {selectField('priority_id', 'Prioridad', options('priority'))}
      </div>

      {selectField('type_id', 'Tipo', options('task_type'))}

      <div className="grid gap-5 sm:grid-cols-2">
        <FormField label="Vence el" required={!!prefix} optional={!prefix} error={error('due_at')}>
          {(p) => <Input {...p} type="datetime-local" {...form.register(name('due_at'))} />}
        </FormField>
        <FormField label="Recordar el" optional error={error('remind_at')}>
          {(p) => <Input {...p} type="datetime-local" {...form.register(name('remind_at'))} />}
        </FormField>
      </div>
      {children}
    </>
  )
}
