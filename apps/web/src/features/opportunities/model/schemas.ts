import { z } from 'zod'

export const opportunityFormSchema = z.object({
  title: z.string().min(2, 'Mínimo 2 caracteres').max(200),
  description: z.string().max(5000).nullable().optional(),
  stage_id: z.string().uuid('Selecciona una etapa'),
  // Obligatorio salvo en Cerrado perdido (se valida en el formulario según la etapa).
  type_id: z.string().nullable().optional(),
  loss_reason_id: z.string().uuid().nullable().optional(),
  owner_id: z.string().uuid().nullable().optional(),
  estimated_amount: z.coerce.number().min(0).nullable().optional(),
  probability: z.coerce.number().min(0).max(100).nullable().optional(),
  expected_close_date: z.string().nullable().optional(),
})

export type OpportunityFormValues = z.infer<typeof opportunityFormSchema>
