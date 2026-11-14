import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm, type Resolver } from 'react-hook-form'
import { Plus, X } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import { opportunitiesService, type Opportunity } from '@/features/opportunities/api/opportunities-service'
import { tasksKeys, type Task } from '@/features/tasks/api/tasks-service'
import { TaskFields } from '@/features/tasks/components/TaskFields'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { errorMessage } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useSessionStore } from '@/shared/auth/session-store'
import { emptyToNull, fromISOString, toISOString } from '@/shared/lib/forms'
import { Input, Textarea } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'

import { interactionsKeys, interactionsService, type Interaction } from '../api/interactions-service'
import { interactionFormSchema, type InteractionFormValues } from '../model/schemas'

function taskToFormValues(t: Task) {
  return {
    title: t.title,
    description: t.description ?? '',
    assignee_id: t.assignee?.id ?? null,
    type_id: t.type?.id ?? null,
    priority_id: t.priority?.id ?? null,
    due_at: fromISOString(t.due_at),
    remind_at: fromISOString(t.remind_at),
  }
}

function daysFromNowAt9(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  d.setHours(9, 0, 0, 0)
  return fromISOString(d.toISOString())
}

/** Aviso previo: qué hará el resultado elegido con las oportunidades del prospecto. */
function resultPipelineHint(code: string | undefined): string | null {
  switch (code) {
    case 'CONTESTO':
      return 'La oportunidad elegida quedará en etapa Nuevo (o se creará una nueva).'
    case 'DEMOSTRACION':
      return 'La oportunidad elegida pasará a la etapa Demostración.'
    case 'COTIZACION':
      return 'La oportunidad elegida pasará a la etapa Cotización.'
    case 'VENTA':
      return 'La oportunidad elegida se cerrará como Ganada.'
    case 'NO_INTERESADO':
      return 'La oportunidad elegida se cerrará como Perdida; si no hay ninguna abierta, se registrará una como Cerrado perdido.'
    default:
      return null
  }
}

/** Resultados que mueven el pipeline y por tanto necesitan saber a qué oportunidad aplican. */
const PIPELINE_RESULTS = ['CONTESTO', 'DEMOSTRACION', 'COTIZACION', 'VENTA', 'NO_INTERESADO']
const CLOSED_STAGES = ['CERRADO_GANADO', 'CERRADO_PERDIDO']
const NEW_OPPORTUNITY = 'new'

function opportunityToast(action: string | null | undefined, stage: string | undefined): string | undefined {
  if (!action || !stage) return undefined
  if (action === 'created') return `Oportunidad creada en etapa ${stage}`
  if (action === 'closed') return `Oportunidad cerrada: ${stage}`
  return `Oportunidad movida a ${stage}`
}

export function InteractionFormSheet({
  prospectId,
  contacts,
  interaction,
  onClose,
}: {
  prospectId: string
  contacts: { id: string; full_name: string }[]
  interaction: Interaction | 'new' | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const isNew = interaction === 'new'
  const editing = interaction && interaction !== 'new' ? interaction : null

  const catalogs = useCatalogBundle(['contact_channel', 'contact_result', 'interest_level', 'opportunity_type'])

  const defaultValues: InteractionFormValues = useMemo(
    () => ({
      occurred_at: editing ? fromISOString(editing.occurred_at) : fromISOString(new Date().toISOString()),
      channel_id: editing?.channel.id ?? '',
      result_id: editing?.result.id ?? '',
      interest_level_id: editing?.interest_level?.id ?? null,
      contact_id: editing?.contact?.id ?? null,
      notes: editing?.notes ?? '',
      opportunity_choice: null,
      new_opportunity_title: '',
      new_opportunity_type_id: null,
      follow_up_task: editing?.follow_up_task ? taskToFormValues(editing.follow_up_task) : null,
    }),
    [interaction], // eslint-disable-line react-hooks/exhaustive-deps
  )

  const form = useForm<InteractionFormValues>({
    resolver: zodResolver(interactionFormSchema) as Resolver<InteractionFormValues>,
    defaultValues,
  })

  const { can } = usePermissions()
  const canManageOpportunities = can(P.OPPORTUNITIES_MANAGE)
  const selectedResultId = form.watch('result_id')
  const selectedResultCode = catalogs.data?.contact_result?.find((o) => o.id === selectedResultId)?.code
  const pipelineHint = resultPipelineHint(selectedResultCode)

  // Oportunidades abiertas del prospecto: la interacción debe aplicarse a una de ellas o crear otra.
  const affectsPipeline =
    canManageOpportunities && !!selectedResultCode && PIPELINE_RESULTS.includes(selectedResultCode)
  const prospectOpps = useQuery({
    queryKey: ['opportunities', 'open-for-interaction', prospectId],
    queryFn: () => opportunitiesService.list({ prospect_id: prospectId }),
    enabled: !!interaction && affectsPipeline,
  })
  const openOpps: Opportunity[] = useMemo(
    () => (prospectOpps.data?.items ?? []).filter((o) => !CLOSED_STAGES.includes(o.stage.code)),
    [prospectOpps.data],
  )
  const mustCreate = selectedResultCode !== 'NO_INTERESADO' && openOpps.length === 0
  const choice = form.watch('opportunity_choice')

  // Valor por defecto: la ya ligada (al editar), la única abierta, o crear nueva si no hay ninguna.
  useEffect(() => {
    if (!affectsPipeline || !prospectOpps.isSuccess) return
    const current = form.getValues('opportunity_choice')
    if (current && (current === NEW_OPPORTUNITY ? mustCreate || openOpps.length > 0 : openOpps.some((o) => o.id === current))) {
      return
    }
    const linkedId = editing?.opportunity?.id
    if (linkedId && openOpps.some((o) => o.id === linkedId)) form.setValue('opportunity_choice', linkedId)
    else if (openOpps.length === 1) form.setValue('opportunity_choice', openOpps[0]!.id)
    else if (mustCreate) form.setValue('opportunity_choice', NEW_OPPORTUNITY)
    else form.setValue('opportunity_choice', null)
  }, [affectsPipeline, prospectOpps.isSuccess, openOpps, mustCreate]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (interaction) form.reset(defaultValues)
  }, [interaction, defaultValues]) // eslint-disable-line react-hooks/exhaustive-deps

  // La próxima acción es una tarea: el bloque se abre con el botón y los campos son los de Tareas.
  const canAddNextAction = can(P.TASKS_MANAGE)
  const currentUserId = useSessionStore((s) => s.user?.id)
  const followUp = form.watch('follow_up_task')
  const hadFollowUp = !!editing?.follow_up_task

  const openNextAction = () =>
    form.setValue(
      'follow_up_task',
      { title: '', description: '', assignee_id: currentUserId ?? null, type_id: null, priority_id: null, due_at: '', remind_at: '' },
      { shouldDirty: true },
    )
  const removeNextAction = () => {
    form.clearErrors('follow_up_task')
    form.setValue('follow_up_task', null, { shouldDirty: true })
  }

  const save = useMutation({
    mutationFn: async (values: InteractionFormValues) => {
      const body = {
        occurred_at: toISOString(values.occurred_at),
        channel_id: values.channel_id,
        result_id: values.result_id,
        interest_level_id: emptyToNull(values.interest_level_id),
        contact_id: emptyToNull(values.contact_id),
        notes: emptyToNull(values.notes),
      }
      const oppFields: Record<string, unknown> = {}
      const resultChanged = isNew || values.result_id !== editing?.result.id
      if (affectsPipeline && resultChanged) {
        if (values.opportunity_choice === NEW_OPPORTUNITY) {
          oppFields.new_opportunity = {
            title: (values.new_opportunity_title ?? '').trim(),
            type_id: values.new_opportunity_type_id,
          }
        } else if (values.opportunity_choice) {
          oppFields.opportunity_id = values.opportunity_choice
        }
      }
      const t = values.follow_up_task
      const follow_up_task = t
        ? {
            title: t.title.trim(),
            description: emptyToNull(t.description),
            assignee_id: emptyToNull(t.assignee_id),
            type_id: emptyToNull(t.type_id),
            priority_id: emptyToNull(t.priority_id),
            due_at: toISOString(t.due_at),
            remind_at: t.remind_at ? toISOString(t.remind_at) : null,
          }
        : null
      if (isNew) {
        return interactionsService.create(prospectId, { ...body, ...oppFields, follow_up_task } as never)
      }
      return interactionsService.update(prospectId, editing!.id, {
        ...body,
        ...oppFields,
        follow_up_task,
        remove_follow_up_task: !follow_up_task && hadFollowUp,
      } as never)
    },
    onSuccess: (saved) => {
      const oppLabel = opportunityToast(saved.opportunity_action, saved.opportunity?.stage.name)
      toast.success(isNew ? 'Interacción registrada' : 'Interacción actualizada', { description: oppLabel })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      queryClient.invalidateQueries({ queryKey: interactionsKeys.list(prospectId) })
      queryClient.invalidateQueries({ queryKey: tasksKeys.all })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['prospects', 'detail', prospectId] })
      onClose()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const selectOptions = (code: 'contact_channel' | 'contact_result' | 'interest_level' | 'opportunity_type') =>
    (catalogs.data?.[code] ?? []).map((o) => ({ value: o.id, label: o.name }))

  const contactOptions = contacts.map((c) => ({ value: c.id, label: c.full_name }))

  return (
    <Sheet open={!!interaction} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={isNew ? 'Registrar interacción' : 'Editar interacción'}
        description={isNew ? 'Anota el resultado del contacto con el prospecto.' : `Intento #${editing?.attempt_number}`}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" form="interaction-form" loading={save.isPending}>
              {isNew ? 'Registrar' : 'Guardar cambios'}
            </Button>
          </>
        }
      >
        <form
          id="interaction-form"
          onSubmit={form.handleSubmit((d) => {
            if (affectsPipeline && (isNew || d.result_id !== editing?.result.id)) {
              const lostWithoutOpen = selectedResultCode === 'NO_INTERESADO' && openOpps.length === 0
              if (!d.opportunity_choice && !lostWithoutOpen) {
                form.setError('opportunity_choice', { message: 'Elige la oportunidad a la que aplica este resultado' })
                return
              }
              if (d.opportunity_choice === NEW_OPPORTUNITY) {
                let invalid = false
                if ((d.new_opportunity_title ?? '').trim().length < 2) {
                  form.setError('new_opportunity_title', { message: 'Escribe el nombre de la oportunidad' })
                  invalid = true
                }
                if (!d.new_opportunity_type_id) {
                  form.setError('new_opportunity_type_id', { message: 'Indica qué se vende' })
                  invalid = true
                }
                if (invalid) return
              }
            }
            save.mutate(d)
          })}
          className="space-y-5"
          noValidate
        >
          <FormField label="Fecha y hora" required error={form.formState.errors.occurred_at?.message}>
            {(p) => <Input {...p} type="datetime-local" {...form.register('occurred_at')} />}
          </FormField>

          <FormField label="Canal" required error={form.formState.errors.channel_id?.message}>
            {(p) => (
              <Controller
                control={form.control}
                name="channel_id"
                render={({ field }) => (
                  <Select
                    {...p}
                    value={field.value}
                    onValueChange={field.onChange}
                    options={selectOptions('contact_channel')}
                    placeholder="Selecciona…"
                  />
                )}
              />
            )}
          </FormField>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Resultado" required error={form.formState.errors.result_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="result_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value}
                      onValueChange={field.onChange}
                      options={selectOptions('contact_result')}
                      placeholder="Selecciona…"
                    />
                  )}
                />
              )}
            </FormField>

            <FormField label="Nivel de interés" optional error={form.formState.errors.interest_level_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="interest_level_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value ?? ''}
                      onValueChange={(v) => field.onChange(v || null)}
                      options={selectOptions('interest_level')}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
          </div>
          {pipelineHint && (
            <p className="-mt-2 rounded-md bg-brand-50 px-3 py-2 text-xs text-brand-700">{pipelineHint}</p>
          )}

          {affectsPipeline && prospectOpps.isSuccess && (openOpps.length > 0 || selectedResultCode !== 'NO_INTERESADO') && (
            <div className="space-y-4 rounded-lg border border-zinc-200 p-3">
              <FormField label="Oportunidad" required error={form.formState.errors.opportunity_choice?.message}>
                {(p) => (
                  <Controller
                    control={form.control}
                    name="opportunity_choice"
                    render={({ field }) => (
                      <Select
                        {...p}
                        value={field.value ?? ''}
                        onValueChange={(v) => {
                          field.onChange(v || null)
                          form.clearErrors('opportunity_choice')
                        }}
                        options={[
                          ...openOpps.map((o) => ({ value: o.id, label: `${o.title} · ${o.stage.name}` })),
                          ...(selectedResultCode === 'NO_INTERESADO'
                            ? []
                            : [{ value: NEW_OPPORTUNITY, label: '+ Nueva oportunidad' }]),
                        ]}
                        placeholder="Selecciona…"
                      />
                    )}
                  />
                )}
              </FormField>
              {choice === NEW_OPPORTUNITY && (
                <>
                  <FormField
                    label="Nombre de la oportunidad"
                    required
                    error={form.formState.errors.new_opportunity_title?.message}
                  >
                    {(p) => (
                      <Input
                        {...p}
                        placeholder="Ej. DS-CONT Empresarial 2 terminales + usuario"
                        {...form.register('new_opportunity_title')}
                      />
                    )}
                  </FormField>
                  <FormField label="Qué se vende" required error={form.formState.errors.new_opportunity_type_id?.message}>
                    {(p) => (
                      <Controller
                        control={form.control}
                        name="new_opportunity_type_id"
                        render={({ field }) => (
                          <Select
                            {...p}
                            value={field.value ?? ''}
                            onValueChange={(v) => field.onChange(v || null)}
                            options={selectOptions('opportunity_type')}
                            placeholder="Selecciona…"
                          />
                        )}
                      />
                    )}
                  </FormField>
                </>
              )}
            </div>
          )}

          {contactOptions.length > 0 && (
            <FormField label="Contacto" optional error={form.formState.errors.contact_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="contact_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value ?? ''}
                      onValueChange={(v) => field.onChange(v || null)}
                      options={contactOptions}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
          )}

          <FormField label="Notas" optional error={form.formState.errors.notes?.message}>
            {(p) => <Textarea {...p} rows={3} {...form.register('notes')} />}
          </FormField>

          {canAddNextAction &&
            (followUp ? (
              <div className="space-y-5 rounded-lg border border-zinc-200 p-3">
                <div className="flex items-center justify-between">
                  <p className="text-[13px] font-medium text-zinc-700">Próxima acción (se crea como tarea)</p>
                  <Button type="button" variant="ghost" size="sm" onClick={removeNextAction}>
                    <X className="h-4 w-4" /> Quitar
                  </Button>
                </div>
                <TaskFields form={form} prefix="follow_up_task">
                  <div className="flex flex-wrap gap-2">
                    {[
                      { label: 'Mañana', days: 1 },
                      { label: 'En 3 días', days: 3 },
                      { label: 'En 1 semana', days: 7 },
                    ].map((s) => (
                      <Button
                        key={s.days}
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => form.setValue('follow_up_task.due_at', daysFromNowAt9(s.days), { shouldValidate: true })}
                      >
                        {s.label}
                      </Button>
                    ))}
                  </div>
                </TaskFields>
              </div>
            ) : (
              <Button type="button" variant="outline" onClick={openNextAction}>
                <Plus className="h-4 w-4" /> Añadir próxima acción
              </Button>
            ))}
        </form>
      </SheetContent>
    </Sheet>
  )
}
