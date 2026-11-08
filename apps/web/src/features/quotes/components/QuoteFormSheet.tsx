import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { Controller, useFieldArray, useForm, type Resolver } from 'react-hook-form'
import { useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { productsKeys, productsService } from '@/features/products/api/products-service'
import { Button } from '@/shared/ui/button'
import { Input, Textarea } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'
import { formatMoney } from '@/shared/lib/format'

import { quotesKeys, quotesService, type Quote } from '../api/quotes-service'
import { quoteFormSchema, type QuoteFormValues } from '../model/schemas'

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

export function QuoteFormSheet({
  prospectId,
  quote,
  onClose,
}: {
  prospectId: string
  quote: Quote | 'new' | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const isNew = quote === 'new'
  const editing = quote && quote !== 'new' ? quote : null

  const productsQ = useQuery({
    queryKey: productsKeys.list({ status: 'active', page: 1 }),
    queryFn: () => productsService.list({ status: 'active', page: 1 }),
  })

  const defaultValues: QuoteFormValues = useMemo(
    () => ({
      opportunity_id: editing?.opportunity?.id ?? null,
      issue_date: editing?.issue_date ? fromDateString(editing.issue_date) : new Date().toISOString().split('T')[0],
      expiration_date: editing?.expiration_date ? fromDateString(editing.expiration_date) : '',
      notes: editing?.notes ?? '',
      items:
        editing?.items.map((i) => ({
          product_id: i.product?.id ?? null,
          description: i.description,
          quantity: i.quantity,
          unit_price: Number(i.unit_price),
        })) ?? [{ product_id: null, description: '', quantity: 1, unit_price: 0 }],
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [quote],
  )

  const form = useForm<QuoteFormValues>({
    resolver: zodResolver(quoteFormSchema) as Resolver<QuoteFormValues>,
    defaultValues,
  })

  const items = useFieldArray({ control: form.control, name: 'items' })

  useEffect(() => {
    if (quote) form.reset(defaultValues)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quote, defaultValues])

  const save = useMutation({
    mutationFn: async (values: QuoteFormValues) => {
      const base = {
        opportunity_id: emptyToNull(values.opportunity_id),
        issue_date: values.issue_date,
        expiration_date: values.expiration_date || null,
        notes: emptyToNull(values.notes),
        items: values.items.map((i) => ({
          product_id: emptyToNull(i.product_id),
          description: i.description,
          quantity: i.quantity,
          unit_price: i.unit_price,
        })),
      }
      if (isNew) {
        return quotesService.create({ prospect_id: prospectId, ...base })
      }
      return quotesService.update(editing!.id, base)
    },
    onSuccess: () => {
      toast.success(isNew ? 'Cotización creada' : 'Cotización actualizada')
      queryClient.invalidateQueries({ queryKey: quotesKeys.all })
      queryClient.invalidateQueries({ queryKey: ['prospects'] })
      onClose()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const productOptions = (productsQ.data?.items ?? []).map((p) => ({
    value: p.id,
    label: `${p.name} (${formatMoney(Number(p.list_price))})`,
  }))

  return (
    <Sheet open={!!quote} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={isNew ? 'Nueva cotización' : 'Editar cotización'}
        description={isNew ? 'Agrega productos o servicios.' : `Cotización de ${editing?.prospect.display_name}`}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" form="quote-form" loading={save.isPending}>
              {isNew ? 'Crear cotización' : 'Guardar cambios'}
            </Button>
          </>
        }
      >
        <form
          id="quote-form"
          onSubmit={form.handleSubmit((d) => save.mutate(d))}
          className="space-y-5"
          noValidate
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Fecha de emisión" required error={form.formState.errors.issue_date?.message}>
              {(p) => <Input {...p} type="date" {...form.register('issue_date')} />}
            </FormField>
            <FormField label="Válido hasta" optional error={form.formState.errors.expiration_date?.message}>
              {(p) => <Input {...p} type="date" {...form.register('expiration_date')} />}
            </FormField>
          </div>

          <FormField label="Notas" optional error={form.formState.errors.notes?.message}>
            {(p) => <Textarea {...p} rows={2} {...form.register('notes')} />}
          </FormField>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-zinc-900">Ítems</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => items.append({ product_id: null, description: '', quantity: 1, unit_price: 0 })}
              >
                <Plus className="size-4" /> Agregar ítem
              </Button>
            </div>

            {items.fields.map((field, index) => (
              <div key={field.id} className="rounded-lg border border-zinc-200 p-3 space-y-3">
                <div className="flex items-start gap-2">
                  <Controller
                    control={form.control}
                    name={`items.${index}.product_id`}
                    render={({ field }) => (
                      <Select
                        value={field.value ?? ''}
                        onValueChange={(v) => {
                          field.onChange(v || null)
                          const product = productsQ.data?.items.find((p) => p.id === v)
                          if (product) {
                            form.setValue(`items.${index}.description`, product.name)
                            form.setValue(`items.${index}.unit_price`, Number(product.list_price))
                          }
                        }}
                        options={productOptions}
                        placeholder="Seleccionar producto…"
                        className="flex-1"
                      />
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    className="text-red-600"
                    onClick={() => items.remove(index)}
                    disabled={items.fields.length === 1}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
                <Input
                  placeholder="Descripción"
                  {...form.register(`items.${index}.description`)}
                />
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    min={1}
                    placeholder="Cantidad"
                    {...form.register(`items.${index}.quantity`)}
                  />
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Precio unitario"
                    {...form.register(`items.${index}.unit_price`)}
                  />
                </div>
              </div>
            ))}
            {form.formState.errors.items?.root && (
              <p className="text-xs font-medium text-red-600">{form.formState.errors.items.root.message}</p>
            )}
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
