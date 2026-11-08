import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm, type Resolver } from 'react-hook-form'
import { useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { errorMessage } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'
import { Input, Textarea } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'

import { interactionsKeys, interactionsService, type Interaction } from '../api/interactions-service'
import { interactionFormSchema, type InteractionFormValues } from '../model/schemas'

function emptyToNull<T>(v: T): T | null {
  if (v === '' || v === undefined) return null
  return v
}

function toISOString(value: string): string {
  if (!value) return ''
  // El input datetime-local no incluye Z; lo convertimos a ISO con zona local.
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toISOString()
}

function fromISOString(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  // Formato datetime-local: YYYY-MM-DDTHH:mm
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
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

  const catalogs = useCatalogBundle(['contact_channel', 'contact_mode', 'contact_result', 'interest_level'])

  const defaultValues: InteractionFormValues = useMemo(
    () => ({
      occurred_at: editing ? fromISOString(editing.occurred_at) : fromISOString(new Date().toISOString()),
      channel_id: editing?.channel.id ?? '',
      mode_id: editing?.mode?.id ?? null,
      result_id: editing?.result.id ?? '',
      interest_level_id: editing?.interest_level?.id ?? null,
      contact_id: editing?.contact?.id ?? null,
      notes: editing?.notes ?? '',
      next_action_desc: editing?.next_action_desc ?? '',
      next_action_at: editing?.next_action_at ? fromISOString(editing.next_action_at) : '',
    }),
    [interaction], // eslint-disable-line react-hooks/exhaustive-deps
  )

  const form = useForm<InteractionFormValues>({
    resolver: zodResolver(interactionFormSchema) as Resolver<InteractionFormValues>,
    defaultValues,
  })

  useEffect(() => {
    if (interaction) form.reset(defaultValues)
  }, [interaction, defaultValues]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: async (values: InteractionFormValues) => {
      const body = {
        occurred_at: toISOString(values.occurred_at),
        channel_id: values.channel_id,
        mode_id: emptyToNull(values.mode_id),
        result_id: values.result_id,
        interest_level_id: emptyToNull(values.interest_level_id),
        contact_id: emptyToNull(values.contact_id),
        notes: emptyToNull(values.notes),
        next_action_desc: emptyToNull(values.next_action_desc),
        next_action_at: values.next_action_at ? toISOString(values.next_action_at) : null,
      }
      if (isNew) {
        return interactionsService.create(prospectId, body)
      }
      return interactionsService.update(prospectId, editing!.id, body)
    },
    onSuccess: () => {
      toast.success(isNew ? 'Interacción registrada' : 'Interacción actualizada')
      queryClient.invalidateQueries({ queryKey: interactionsKeys.list(prospectId) })
      queryClient.invalidateQueries({ queryKey: ['prospects', 'detail', prospectId] })
      onClose()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const selectOptions = (code: 'contact_channel' | 'contact_mode' | 'contact_result' | 'interest_level') =>
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
          onSubmit={form.handleSubmit((d) => save.mutate(d))}
          className="space-y-5"
          noValidate
        >
          <FormField label="Fecha y hora" required error={form.formState.errors.occurred_at?.message}>
            {(p) => <Input {...p} type="datetime-local" {...form.register('occurred_at')} />}
          </FormField>

          <div className="grid gap-5 sm:grid-cols-2">
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

            <FormField label="Modalidad" optional error={form.formState.errors.mode_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="mode_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value ?? ''}
                      onValueChange={(v) => field.onChange(v || null)}
                      options={selectOptions('contact_mode')}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
          </div>

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

          <div className="rounded-lg border border-zinc-200 p-3 space-y-4">
            <p className="text-[13px] font-medium text-zinc-700">Próxima acción</p>
            <FormField label="Descripción" optional error={form.formState.errors.next_action_desc?.message}>
              {(p) => <Input {...p} {...form.register('next_action_desc')} placeholder="Ej: Enviar cotización" />}
            </FormField>
            <FormField label="Fecha y hora" optional error={form.formState.errors.next_action_at?.message}>
              {(p) => <Input {...p} type="datetime-local" {...form.register('next_action_at')} />}
            </FormField>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
