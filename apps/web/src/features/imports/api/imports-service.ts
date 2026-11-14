import { api, type Schemas, unwrap } from '@/shared/api/client'
import { useSessionStore } from '@/shared/auth/session-store'

export type ImportJob = Schemas['ImportJobRead']
export type ImportJobDetail = Schemas['ImportJobDetailRead']
export type ImportPreview = Schemas['ImportPreview']
export type WeeklyReport = Schemas['WeeklyReport']
export type WeeklyDetailItem = Schemas['WeeklyDetailItem']

export interface WeeklyFilters {
  date?: string
  date_from?: string
  date_to?: string
  seller_id?: string
  product_id?: string
  type_id?: string
}

function cleanFilters(f: WeeklyFilters) {
  return Object.fromEntries(Object.entries(f).filter(([, v]) => !!v)) as WeeklyFilters
}

export const importsKeys = {
  all: ['imports'] as const,
  jobs: () => ['imports', 'jobs'] as const,
  job: (id: string) => ['imports', 'job', id] as const,
  preview: () => ['imports', 'preview'] as const,
  weeklyReport: (f: WeeklyFilters) => ['imports', 'weekly-report', f] as const,
  weeklyDetail: (f: WeeklyFilters, key: string, period: string) => ['imports', 'weekly-detail', f, key, period] as const,
}

async function uploadFile(path: string, file: File): Promise<unknown> {
  const token = useSessionStore.getState().accessToken ?? ''
  const body = new FormData()
  body.append('file', file)
  const res = await fetch(`${window.location.origin}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body,
    credentials: 'same-origin',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Error desconocido' } }))
    throw new Error(err.error?.message || `Error ${res.status}`)
  }
  return res.json()
}

export const importsService = {
  preview: (file: File) => uploadFile('/api/v1/imports/for-ven-001/preview', file) as Promise<ImportPreview>,
  import: (file: File) => uploadFile('/api/v1/imports/for-ven-001', file) as Promise<ImportJobDetail>,
  list: () => unwrap(api.GET('/api/v1/imports')),
  get: (id: string) => unwrap(api.GET('/api/v1/imports/{job_id}', { params: { path: { job_id: id } } })),
  weeklyReport: (f: WeeklyFilters = {}) => unwrap(api.GET('/api/v1/reports/weekly', { params: { query: cleanFilters(f) } })),
  weeklyDetail: (f: WeeklyFilters, key: string, period: string) =>
    unwrap(api.GET('/api/v1/reports/weekly/detail', { params: { query: { ...cleanFilters(f), key, period } } })),
  exportWeeklyReport: async (f: WeeklyFilters = {}) => {
    const token = useSessionStore.getState().accessToken ?? ''
    const query = new URLSearchParams(cleanFilters(f) as Record<string, string>).toString()
    const res = await fetch(`${window.location.origin}/api/v1/reports/weekly/export${query ? `?${query}` : ''}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'same-origin',
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: { message: 'Error desconocido' } }))
      throw new Error(err.error?.message || `Error ${res.status}`)
    }
    return res.blob()
  },
}
