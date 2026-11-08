import { z } from 'zod'

export const prospectContactSchema = z.object({
  full_name: z.string().min(2, 'Nombre completo requerido.'),
  position: z.string().optional(),
  area: z.string().optional(),
  email: z.string().email('Correo inválido.').optional().or(z.literal('')),
  phone: z.string().optional(),
  whatsapp: z.string().optional(),
  is_primary: z.boolean().default(false),
  notes: z.string().optional(),
})

export const prospectFormSchema = z
  .object({
    person_type: z.enum(['NATURAL', 'JURIDICA']),
    document_type_id: z.string().uuid().optional().or(z.literal('')),
    document_number: z.string().max(20).optional().or(z.literal('')),
    first_name: z.string().max(100).optional().or(z.literal('')),
    last_name: z.string().max(100).optional().or(z.literal('')),
    birth_date: z.string().optional().or(z.literal('')),
    legal_name: z.string().max(200).optional().or(z.literal('')),
    trade_name: z.string().max(200).optional().or(z.literal('')),
    email: z.string().email('Correo inválido.').optional().or(z.literal('')),
    phone: z.string().max(30).optional().or(z.literal('')),
    phone_alt: z.string().max(30).optional().or(z.literal('')),
    whatsapp: z.string().max(30).optional().or(z.literal('')),
    address: z.string().max(1000).optional().or(z.literal('')),
    source_id: z.string().uuid().optional().or(z.literal('')),
    acquisition_channel_id: z.string().uuid().optional().or(z.literal('')),
    interest_level_id: z.string().uuid().optional().or(z.literal('')),
    priority_id: z.string().uuid().optional().or(z.literal('')),
    owner_id: z.string().uuid().optional().or(z.literal('')),
    notes: z.string().max(5000).optional().or(z.literal('')),
    tags: z.array(z.string().uuid()).optional(),
    contacts: z.array(prospectContactSchema).optional(),
  })
  .superRefine((data, ctx) => {
    if (data.person_type === 'NATURAL') {
      if (!data.first_name?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['first_name'], message: 'Ingresa el nombre.' })
      }
      if (!data.last_name?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['last_name'], message: 'Ingresa el apellido.' })
      }
    } else {
      if (!data.legal_name?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['legal_name'], message: 'Ingresa la razón social.' })
      }
    }
  })

export type ProspectFormValues = z.infer<typeof prospectFormSchema>
