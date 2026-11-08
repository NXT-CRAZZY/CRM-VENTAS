import { api, type Schemas, unwrap } from '@/shared/api/client'

export type SalesDashboard = Schemas['SalesDashboardRead']
export type ManagementDashboard = Schemas['ManagementDashboardRead']

export const dashboardService = {
  sales: () => unwrap(api.GET('/api/v1/dashboard/sales')),
  management: () => unwrap(api.GET('/api/v1/dashboard/management')),
}

