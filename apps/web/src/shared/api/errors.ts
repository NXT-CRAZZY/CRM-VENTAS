export interface FieldError {
  field: string
  message: string
}

interface ErrorBody {
  error?: { code?: string; message?: string; details?: unknown }
}

/** Error de API con mensaje listo para mostrar al usuario (nunca detalles técnicos). */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, body: unknown) {
    const err = (body as ErrorBody | undefined)?.error
    super(err?.message ?? fallbackMessage(status))
    this.name = 'ApiError'
    this.status = status
    this.code = err?.code ?? 'UNKNOWN'
    this.details = err?.details
  }

  /** Errores por campo (validación) para mostrarlos junto al input correspondiente. */
  get fieldErrors(): FieldError[] {
    return Array.isArray(this.details)
      ? (this.details as FieldError[]).filter((d) => d && typeof d.field === 'string')
      : []
  }
}

function fallbackMessage(status: number) {
  if (status === 0) return 'No se pudo conectar con el servidor. Revisa tu conexión.'
  if (status === 403) return 'No tienes permiso para realizar esta acción.'
  if (status === 404) return 'El registro no existe o fue eliminado.'
  if (status >= 500) return 'Ocurrió un error inesperado. Intenta nuevamente.'
  return 'No se pudo completar la operación.'
}

export function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message
  return 'Ocurrió un error inesperado. Intenta nuevamente.'
}
