import type { FieldValues, Path, UseFormReturn } from 'react-hook-form'
import { toast } from 'sonner'
import { ApiError, errorMessage } from '@/shared/api/errors'

/**
 * Muestra los errores del backend junto a cada campo del formulario; si el error no
 * corresponde a un campo, lo muestra como notificación.
 * `codeToField` asocia códigos de negocio (p.ej. EMAIL_TAKEN) a un campo.
 */
export function handleFormError<T extends FieldValues>(
  form: UseFormReturn<T>,
  error: unknown,
  codeToField: Record<string, Path<T>> = {},
) {
  if (error instanceof ApiError) {
    const target = codeToField[error.code]
    if (target) {
      form.setError(target, { message: error.message }, { shouldFocus: true })
      return
    }
    const fields = error.fieldErrors.filter((f) => f.field in form.getValues())
    if (fields.length) {
      fields.forEach((f, i) => form.setError(f.field as Path<T>, { message: f.message }, { shouldFocus: i === 0 }))
      return
    }
  }
  toast.error(errorMessage(error))
}

/** Contraseña temporal legible (sin caracteres ambiguos) que cumple la política. */
export function generateTempPassword() {
  const letters = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
  const digits = '23456789'
  const pick = (set: string) => set[crypto.getRandomValues(new Uint32Array(1))[0] % set.length]
  return Array.from({ length: 6 }, () => pick(letters)).join('') + pick(digits) + pick(digits) + pick(digits)
}

export function emptyToNull<T>(v: T): T | null {
  if (v === '' || v === undefined) return null
  return v
}

/** Valor de un input datetime-local (hora local) → ISO UTC para la API. */
export function toISOString(value: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toISOString()
}

/** ISO de la API → valor para un input datetime-local (YYYY-MM-DDTHH:mm, hora local). */
export function fromISOString(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
