import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Alert = Schemas['AlertRead']
export type AlertStatus = Schemas['AlertRead']['status']
export type AlertSeverity = Schemas['AlertRead']['severity']

export const alertsService = {
  list: (params?: { status?: AlertStatus; severity?: AlertSeverity; page?: number; page_size?: number }) =>
    unwrap(api.GET('/api/v1/alerts', { params: { query: params } })),
  unreadCount: () => unwrap(api.GET('/api/v1/alerts/unread-count')),
  generate: () => unwrap(api.POST('/api/v1/alerts/generate')),
  markRead: (alertId: string) => unwrap(api.PATCH('/api/v1/alerts/{alert_id}/read', { params: { path: { alert_id: alertId } } })),
  dismiss: (alertId: string) => unwrap(api.PATCH('/api/v1/alerts/{alert_id}/dismiss', { params: { path: { alert_id: alertId } } })),
}
