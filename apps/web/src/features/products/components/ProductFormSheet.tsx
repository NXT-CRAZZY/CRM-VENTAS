import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { handleFormError } from '@/shared/lib/forms'
import { Button } from '@/shared/ui/button'
import { Input, Textarea } from '@/shared/ui/input'
import { Select, Switch } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'
import {
  BILLING_LABEL,
  type BillingPeriod,
  KIND_LABEL,
  type Product,
  type ProductKind,
  productsService,
  useProductCategories,
} from '../api/products-service'

const schema = z.object({
  code: z.string().trim().toUpperCase().min(2, 'Ingresa el código.').max(30).regex(/^[A-Z0-9_-]+$/, 'Solo letras, números, - y _.'),
  name: z.string().trim().min(2, 'Ingresa el nombre.').max(200),
  description: z.string().trim().max(2000).optional(),
  category_id: z.string().min(1, 'Selecciona la categoría.'),
  kind: z.enum(['LICENCIA_PERPETUA', 'SUSCRIPCION', 'USUARIO_ADICIONAL', 'DEMO']),
  billing_period: z.enum(['UNICO', 'SEMANAL', 'MENSUAL', 'ANUAL']),
  list_price: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/, 'Ingresa un monto válido (ej. 1470.00).'),
  is_active: z.boolean(),
})
type Form = z.infer<typeof schema>

export function ProductFormSheet({ product, onClose, onSaved }: { product: Product | 'new' | null; onClose: () => void; onSaved: () => void }) {
  const editing = product && product !== 'new' ? product : null
  const categories = useProductCategories()
  const form = useForm<Form>({ resolver: zodResolver(schema) })
  const { errors } = form.formState

  useEffect(() => {
    if (!product) return
    form.reset({
      code: editing?.code ?? '',
      name: editing?.name ?? '',
      description: editing?.description ?? '',
      category_id: editing?.category.id ?? '',
      kind: editing?.kind ?? 'LICENCIA_PERPETUA',
      billing_period: editing?.billing_period ?? 'UNICO',
      list_price: editing ? Number(editing.list_price).toFixed(2) : '',
      is_active: editing?.is_active ?? true,
    })
  }, [product]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: (d: Form) => {
      const body = { ...d, description: d.description || null }
      return editing ? productsService.update(editing.id, body) : productsService.create(body)
    },
    onSuccess: () => {
      toast.success(editing ? 'Producto actualizado' : 'Producto creado')
      onSaved()
      onClose()
    },
    onError: (e) => handleFormError(form, e, { PRODUCT_CODE_TAKEN: 'code' }),
  })

  return (
    <Sheet open={!!product} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={editing ? 'Editar producto' : 'Nuevo producto'}
        description={editing ? editing.code : 'El precio registrado es el precio final de venta.'}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" form="product-form" loading={save.isPending}>Guardar</Button>
          </>
        }
      >
        <form id="product-form" onSubmit={form.handleSubmit((d) => save.mutate(d))} className="space-y-5" noValidate>
          <div className="grid gap-5 sm:grid-cols-[160px_1fr]">
            <FormField label="Código" required error={errors.code?.message}>
              {(p) => <Input {...p} className="font-mono uppercase" {...form.register('code')} />}
            </FormField>
            <FormField label="Precio (S/)" required error={errors.list_price?.message}>
              {(p) => <Input {...p} inputMode="decimal" className="tabular" placeholder="0.00" {...form.register('list_price')} />}
            </FormField>
          </div>
          <FormField label="Nombre" required error={errors.name?.message}>
            {(p) => <Input {...p} {...form.register('name')} />}
          </FormField>
          <FormField label="Categoría" required error={errors.category_id?.message}>
            {(p) => (
              <Controller
                control={form.control}
                name="category_id"
                render={({ field }) => (
                  <Select
                    {...p}
                    value={field.value}
                    onValueChange={field.onChange}
                    options={(categories.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
                  />
                )}
              />
            )}
          </FormField>
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Tipo" required>
              {(p) => (
                <Controller
                  control={form.control}
                  name="kind"
                  render={({ field }) => (
                    <Select {...p} value={field.value} onValueChange={(v) => field.onChange(v as ProductKind)} options={Object.entries(KIND_LABEL).map(([value, label]) => ({ value, label }))} />
                  )}
                />
              )}
            </FormField>
            <FormField label="Periodicidad" required hint="Define la fecha de renovación de lo vendido.">
              {(p) => (
                <Controller
                  control={form.control}
                  name="billing_period"
                  render={({ field }) => (
                    <Select {...p} value={field.value} onValueChange={(v) => field.onChange(v as BillingPeriod)} options={Object.entries(BILLING_LABEL).map(([value, label]) => ({ value, label }))} />
                  )}
                />
              )}
            </FormField>
          </div>
          <FormField label="Descripción" optional>
            {(p) => <Textarea {...p} rows={3} {...form.register('description')} />}
          </FormField>
          {editing && (
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <label className="flex items-center justify-between gap-4 rounded-lg border border-zinc-200 p-3">
                  <span>
                    <span className="block text-sm font-medium text-zinc-900">Disponible para la venta</span>
                    <span className="block text-xs text-muted-foreground">Los productos inactivos no se ofrecen en nuevas cotizaciones.</span>
                  </span>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </label>
              )}
            />
          )}
        </form>
      </SheetContent>
    </Sheet>
  )
}
