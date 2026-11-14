import { z } from 'zod'
import { followUpTaskSchema } from '@/features/tasks/model/schemas'

export const interactionFormSchema = z.object({
  occurred_at: z.string().min(1, 'Indica la fecha y hora'),
  channel_id: z.string().uuid('Selecciona un canal'),
  result_id: z.string().uuid('Selecciona un resultado'),
  interest_level_id: z.string().uuid().nullable().optional(),
  contact_id: z.string().uuid().nullable().optional(),
  notes: z.string().max(5000).nullable().optional(),
  // Oportunidad a la que aplica el resultado: id de una abierta o 'new' para crear una nueva.
  opportunity_choice: z.string().nullable().optional(),
  new_opportunity_title: z.string().max(200).nullable().optional(),
  new_opportunity_type_id: z.string().nullable().optional(),
  // "Añadir próxima acción": tarea de seguimiento vinculada a la interacción (null = sin tarea).
  follow_up_task: followUpTaskSchema.nullable().optional(),
})

export type InteractionFormValues = z.infer<typeof interactionFormSchema>
