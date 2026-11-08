import { z } from 'zod'

export const taskFormSchema = z.object({
  title: z.string().min(2, 'Mínimo 2 caracteres').max(200),
  description: z.string().max(5000).nullable().optional(),
  assignee_id: z.string().uuid().nullable().optional(),
  type_id: z.string().uuid().nullable().optional(),
  priority_id: z.string().uuid().nullable().optional(),
  due_at: z.string().nullable().optional(),
  remind_at: z.string().nullable().optional(),
})

export type TaskFormValues = z.infer<typeof taskFormSchema>
