import { z } from 'zod'

export const interactionFormSchema = z.object({
  occurred_at: z.string().min(1, 'Indica la fecha y hora'),
  channel_id: z.string().uuid('Selecciona un canal'),
  mode_id: z.string().uuid().nullable().optional(),
  result_id: z.string().uuid('Selecciona un resultado'),
  interest_level_id: z.string().uuid().nullable().optional(),
  contact_id: z.string().uuid().nullable().optional(),
  notes: z.string().max(5000).nullable().optional(),
  next_action_desc: z.string().max(200).nullable().optional(),
  next_action_at: z.string().nullable().optional(),
})

export type InteractionFormValues = z.infer<typeof interactionFormSchema>
