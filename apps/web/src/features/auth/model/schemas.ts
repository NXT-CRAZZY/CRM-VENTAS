import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().trim().min(1, 'Ingresa tu correo.').email('Ingresa un correo válido.'),
  password: z.string().min(1, 'Ingresa tu contraseña.'),
})
export type LoginForm = z.infer<typeof loginSchema>

/** Mismas reglas que el backend (users/domain/password_policy.py). */
export const passwordRule = z
  .string()
  .min(8, 'Debe tener al menos 8 caracteres.')
  .regex(/[A-Za-zÁÉÍÓÚáéíóúÑñ]/, 'Debe incluir al menos una letra.')
  .regex(/\d/, 'Debe incluir al menos un número.')

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Ingresa tu contraseña actual.'),
    new_password: passwordRule,
    confirm: z.string(),
  })
  .refine((d) => d.new_password === d.confirm, { path: ['confirm'], message: 'Las contraseñas no coinciden.' })
  .refine((d) => d.new_password !== d.current_password, {
    path: ['new_password'],
    message: 'Debe ser distinta de la actual.',
  })
export type ChangePasswordForm = z.infer<typeof changePasswordSchema>
