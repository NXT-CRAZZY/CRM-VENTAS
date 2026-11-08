import { api, type Schemas, unwrap } from '@/shared/api/client'
import { useSessionStore } from '@/shared/auth/session-store'

export type ImportJob = Schemas['ImportJobRead']
export type ImportJobDetail = Schemas['ImportJobDetailRead']
export type ImportPreview = Schemas['ImportPreview']
export type WeeklyReport = Schemas['WeeklyReport']

export const importsKeys = {
  all: ['imports'] as const,
  jobs: () => ['imports', 'jobs'] as const,
  job: (id: string) => ['imports', 'job', id] as const,
  preview: () => ['imports', 'preview'] as const,
  weeklyReport: (date?: string) => ['imports', 'weekly-report', date] as const,
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
  weeklyReport: (date?: string) =>
    unwrap(api.GET('/api/v1/reports/weekly', { params: { query: { date } } })),
  exportWeeklyReport: async (date?: string) => {
    const token = useSessionStore.getState().accessToken ?? ''
    const query = date ? `?report_date=${encodeURIComponent(date)}` : ''
    const res = await fetch(`${window.location.origin}/api/v1/reports/weekly/export${query}`, {
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
