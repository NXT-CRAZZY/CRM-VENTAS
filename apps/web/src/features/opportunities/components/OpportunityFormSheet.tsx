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

import { opportunitiesKeys, opportunitiesService, type Opportunity } from '../api/opportunities-service'
import { opportunityFormSchema, type OpportunityFormValues } from '../model/schemas'

function emptyToNull<T>(v: T): T | null {
  if (v === '' || v === undefined) return null
  return v
}

function fromDateString(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function OpportunityFormSheet({
  prospectId,
  opportunity,
  onClose,
}: {
  prospectId: string
  opportunity: Opportunity | 'new' | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const isNew = opportunity === 'new'
  const editing = opportunity && opportunity !== 'new' ? opportunity : null

  const catalogs = useCatalogBundle(['pipeline_stage', 'opportunity_type', 'loss_reason'])
  const users = useActiveUsers(true)

  const defaultValues: OpportunityFormValues = useMemo(
    () => ({
      title: editing?.title ?? '',
      description: editing?.description ?? '',
      stage_id: editing?.stage.id ?? '',
      type_id: editing?.type?.id ?? null,
      loss_reason_id: editing?.loss_reason?.id ?? null,
      owner_id: editing?.owner?.id ?? null,
      estimated_amount: editing?.estimated_amount ? Number(editing.estimated_amount) : null,
      probability: editing?.probability ?? null,
      expected_close_date: editing?.expected_close_date ? fromDateString(editing.expected_close_date) : '',
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [opportunity],
  )

  const form = useForm<OpportunityFormValues>({
    resolver: zodResolver(opportunityFormSchema) as Resolver<OpportunityFormValues>,
    defaultValues,
  })

  useEffect(() => {
    if (opportunity) form.reset(defaultValues)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opportunity, defaultValues])

  const save = useMutation({
    mutationFn: async (values: OpportunityFormValues) => {
      const base = {
        title: values.title,
        description: emptyToNull(values.description),
        stage_id: values.stage_id,
        type_id: emptyToNull(values.type_id),
        loss_reason_id: emptyToNull(values.loss_reason_id),
        owner_id: emptyToNull(values.owner_id),
        estimated_amount: values.estimated_amount ?? null,
        probability: values.probability ?? null,
        expected_close_date: values.expected_close_date || null,
      }
      if (isNew) {
        return opportunitiesService.create({ prospect_id: prospectId, ...base })
      }
      return opportunitiesService.update(editing!.id, base)
    },
    onSuccess: () => {
      toast.success(isNew ? 'Oportunidad creada' : 'Oportunidad actualizada')
      queryClient.invalidateQueries({ queryKey: opportunitiesKeys.all })
      onClose()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const selectOptions = (code: 'pipeline_stage' | 'opportunity_type' | 'loss_reason') =>
    (catalogs.data?.[code] ?? []).map((o) => ({ value: o.id, label: o.name }))

  return (
    <Sheet open={!!opportunity} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={isNew ? 'Nueva oportunidad' : 'Editar oportunidad'}
        description={isNew ? 'Registra una oportunidad de venta para este prospecto.' : editing?.title}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" form="opportunity-form" loading={save.isPending}>
              {isNew ? 'Crear oportunidad' : 'Guardar cambios'}
            </Button>
          </>
        }
      >
        <form
          id="opportunity-form"
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
            <FormField label="Etapa" required error={form.formState.errors.stage_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="stage_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value}
                      onValueChange={field.onChange}
                      options={selectOptions('pipeline_stage')}
                      placeholder="Selecciona…"
                    />
                  )}
                />
              )}
            </FormField>

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
                      options={selectOptions('opportunity_type')}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Responsable" optional error={form.formState.errors.owner_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="owner_id"
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

            <FormField label="Motivo de pérdida" optional error={form.formState.errors.loss_reason_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="loss_reason_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value ?? ''}
                      onValueChange={(v) => field.onChange(v || null)}
                      options={selectOptions('loss_reason')}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
          </div>

          <div className="grid gap-5 sm:grid-cols-3">
            <FormField label="Monto estimado" optional error={form.formState.errors.estimated_amount?.message}>
              {(p) => <Input {...p} type="number" min={0} step="0.01" {...form.register('estimated_amount')} />}
            </FormField>

            <FormField label="Probabilidad %" optional error={form.formState.errors.probability?.message}>
              {(p) => <Input {...p} type="number" min={0} max={100} {...form.register('probability')} />}
            </FormField>

            <FormField label="Cierre esperado" optional error={form.formState.errors.expected_close_date?.message}>
              {(p) => <Input {...p} type="date" {...form.register('expected_close_date')} />}
            </FormField>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
