import { z } from 'zod'

export const quoteItemSchema = z.object({
  product_id: z.string().uuid().nullable().optional(),
  description: z.string().min(1, 'Ingresa una descripción').max(255),
  quantity: z.coerce.number().min(1, 'Mínimo 1'),
  unit_price: z.coerce.number().min(0, 'Precio mínimo 0'),
})

export const quoteFormSchema = z.object({
  opportunity_id: z.string().uuid().nullable().optional(),
  issue_date: z.string().min(1, 'Ingresa la fecha de emisión'),
  expiration_date: z.string().nullable().optional(),
  notes: z.string().max(5000).nullable().optional(),
  items: z.array(quoteItemSchema).min(1, 'Agrega al menos un ítem'),
})

export type QuoteItemFormValues = z.infer<typeof quoteItemSchema>
export type QuoteFormValues = z.infer<typeof quoteFormSchema>
