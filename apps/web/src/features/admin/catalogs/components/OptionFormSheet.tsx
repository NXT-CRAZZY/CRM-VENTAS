import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Lock } from 'lucide-react'
import { useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { handleFormError } from '@/shared/lib/forms'
import { ColorBadge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Input, Textarea } from '@/shared/ui/input'
import { Switch } from '@/shared/ui/menus'
import { ColorPicker } from '@/shared/ui/misc'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'
import { type Catalog, type CatalogOption, catalogsService } from '../api/catalogs-service'

const schema = z.object({
  name: z.string().trim().min(1, 'Ingresa un nombre.').max(120),
  code: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z0-9_]*$/, 'Solo letras, números y guion bajo.')
    .max(40)
    .optional(),
  description: z.string().trim().max(500).optional(),
  legacy_code: z.string().trim().max(20).optional(),
  color: z.string().nullable().optional(),
  weight: z.string().optional(),
  is_active: z.boolean(),
})
type Form = z.infer<typeof schema>

export function OptionFormSheet({
  catalog,
  option,
  onClose,
  onSaved,
}: {
  catalog: Catalog
  option: CatalogOption | 'new' | null
  onClose: () => void
  onSaved: () => void
}) {
  const editing = option && option !== 'new' ? option : null
  const form = useForm<Form>({ resolver: zodResolver(schema) })
  const { errors } = form.formState

  useEffect(() => {
    if (!option) return
    form.reset({
      name: editing?.name ?? '',
      code: editing?.code ?? '',
      description: editing?.description ?? '',
      legacy_code: editing?.legacy_code ?? '',
      color: editing?.color ?? null,
      weight: editing?.weight ?? '',
      is_active: editing?.is_active ?? true,
    })
  }, [option]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: (d: Form) => {
      const body = {
        name: d.name,
        code: d.code || null,
        description: d.description || null,
        legacy_code: d.legacy_code || null,
        color: catalog.uses_color ? d.color ?? null : null,
        weight: catalog.uses_weight && d.weight ? d.weight : null,
      }
      return editing
        ? catalogsService.update(editing.id, { ...body, is_active: d.is_active })
        : catalogsService.create(catalog.code, body)
    },
    onSuccess: () => {
      toast.success(editing ? 'Opción actualizada' : 'Opción agregada')
      onSaved()
      onClose()
    },
    onError: (e) => handleFormError(form, e, { OPTION_CODE_TAKEN: 'code', SYSTEM_OPTION: 'is_active' }),
  })

  const name = form.watch('name')
  const color = form.watch('color')

  return (
    <Sheet open={!!option} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={editing ? 'Editar opción' : 'Nueva opción'}
        description={catalog.name}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" form="option-form" loading={save.isPending}>Guardar</Button>
          </>
        }
      >
        <form id="option-form" onSubmit={form.handleSubmit((d) => save.mutate(d))} className="space-y-5" noValidate>
          {editing?.is_system && (
            <p className="flex items-start gap-2 rounded-md bg-zinc-50 px-3 py-2 text-[13px] text-zinc-600">
              <Lock className="mt-0.5 size-3.5 shrink-0" />
              Opción del sistema: puedes cambiar su nombre y color, pero no su código ni desactivarla.
            </p>
          )}
          <FormField label="Nombre visible" required error={errors.name?.message}>
            {(p) => <Input {...p} autoFocus {...form.register('name')} />}
          </FormField>
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Código interno" optional hint={editing ? undefined : 'Se genera del nombre si lo dejas vacío.'} error={errors.code?.message}>
              {(p) => <Input {...p} className="font-mono uppercase" disabled={editing?.is_system} {...form.register('code')} />}
            </FormField>
            <FormField label="Código Excel (legacy)" optional hint="Código usado en FOR-VEN-001." error={errors.legacy_code?.message}>
              {(p) => <Input {...p} className="font-mono" {...form.register('legacy_code')} />}
            </FormField>
          </div>
          <FormField label="Descripción" optional>
            {(p) => <Textarea {...p} rows={2} {...form.register('description')} />}
          </FormField>
          {catalog.uses_color && (
            <FormField label="Color" optional hint="Se usa en etiquetas y gráficos.">
              {() => (
                <div className="space-y-3">
                  <Controller control={form.control} name="color" render={({ field }) => <ColorPicker value={field.value} onChange={field.onChange} />} />
                  <div className="text-xs text-muted-foreground">
                    Vista previa: <ColorBadge color={color}>{name || 'Opción'}</ColorBadge>
                  </div>
                </div>
              )}
            </FormField>
          )}
          {catalog.uses_weight && (
            <FormField label="Peso para puntuación" optional hint="Usado por el lead scoring y estadísticas.">
              {(p) => <Input {...p} type="number" inputMode="decimal" step="0.5" className="sm:max-w-32" {...form.register('weight')} />}
            </FormField>
          )}
          {editing && (
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <label className="flex items-center justify-between gap-4 rounded-lg border border-zinc-200 p-3">
                  <span>
                    <span className="block text-sm font-medium text-zinc-900">Activa</span>
                    <span className="block text-xs text-muted-foreground">Las opciones inactivas no aparecen en formularios, pero se conservan en el historial.</span>
                  </span>
                  <Switch checked={field.value} onCheckedChange={field.onChange} disabled={editing.is_system} />
                </label>
              )}
            />
          )}
          {errors.is_active?.message && <p className="text-xs font-medium text-red-600">{errors.is_active.message}</p>}
        </form>
      </SheetContent>
    </Sheet>
  )
}
