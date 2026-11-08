import type { ProspectStatus } from '../api/prospects-service'

export const STATUS_OPTIONS: { value: ProspectStatus; label: string }[] = [
  { value: 'ACTIVO', label: 'Activos' },
  { value: 'EN_PAUSA', label: 'En pausa' },
  { value: 'DESCARTADO', label: 'Descartados' },
  { value: 'NO_CALIFICA', label: 'No califica' },
  { value: 'INACTIVO', label: 'Inactivos' },
]

export const STATUS_CHANGE_OPTIONS: { value: ProspectStatus; label: string }[] = [
  { value: 'ACTIVO', label: 'Activo' },
  { value: 'EN_PAUSA', label: 'En pausa' },
  { value: 'DESCARTADO', label: 'Descartado' },
  { value: 'NO_CALIFICA', label: 'No califica' },
  { value: 'INACTIVO', label: 'Inactivo' },
]
