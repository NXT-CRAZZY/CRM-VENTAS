// Formatos regionales de Perú: soles y hora de Lima, independientemente del equipo del usuario.
const TZ = 'America/Lima'

const pen = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2 })

export function formatMoney(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return '—'
  return pen.format(Number(value))
}

const dateFmt = new Intl.DateTimeFormat('es-PE', { timeZone: TZ, day: '2-digit', month: 'short', year: 'numeric' })
const dateTimeFmt = new Intl.DateTimeFormat('es-PE', {
  timeZone: TZ,
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDate(value: string | Date | null | undefined) {
  return value ? dateFmt.format(new Date(value)) : '—'
}

export function formatDateTime(value: string | Date | null | undefined) {
  return value ? dateTimeFmt.format(new Date(value)) : '—'
}

/** Formato legible para teléfono peruano (básico: 9xx xxx xxx o 01 xxx xxxx). */
export function formatPhone(value: string | null | undefined) {
  if (!value) return ''
  const digits = value.replace(/\D/g, '')
  if (digits.length === 9 && digits.startsWith('9')) {
    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`
  }
  if (digits.length === 8) {
    return `${digits.slice(0, 4)} ${digits.slice(4)}`
  }
  return value
}

const rtf = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })

export function formatRelative(value: string | Date | null | undefined, now = new Date()) {
  if (!value) return 'Nunca'
  const diffSec = (new Date(value).getTime() - now.getTime()) / 1000
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  for (const [unit, secs] of units) {
    if (Math.abs(diffSec) >= secs) return rtf.format(Math.round(diffSec / secs), unit)
  }
  return 'hace un momento'
}

export function greeting(now = new Date()) {
  const hour = Number(new Intl.DateTimeFormat('es-PE', { timeZone: TZ, hour: 'numeric', hour12: false }).format(now))
  if (hour < 12) return 'Buenos días'
  if (hour < 19) return 'Buenas tardes'
  return 'Buenas noches'
}
