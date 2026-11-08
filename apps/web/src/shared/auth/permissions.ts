import type { ReactNode } from 'react'
import { useSessionStore } from './session-store'

/** Espejo de los códigos de permiso del backend (app/modules/rbac/domain/permissions.py). */
export const P = {
  USERS_READ: 'users.read',
  USERS_MANAGE: 'users.manage',
  ROLES_READ: 'roles.read',
  ROLES_MANAGE: 'roles.manage',
  CATALOGS_MANAGE: 'catalogs.manage',
  PRODUCTS_READ: 'products.read',
  PRODUCTS_MANAGE: 'products.manage',
  SETTINGS_READ: 'settings.read',
  SETTINGS_MANAGE: 'settings.manage',
  AUDIT_READ: 'audit.read',
  DASHBOARD_SALES: 'dashboard.sales',
  DASHBOARD_MANAGEMENT: 'dashboard.management',
  PROSPECTS_READ_OWN: 'prospects.read.own',
  PROSPECTS_READ_ALL: 'prospects.read.all',
  PROSPECTS_CREATE: 'prospects.create',
  PROSPECTS_UPDATE_OWN: 'prospects.update.own',
  PROSPECTS_UPDATE_ALL: 'prospects.update.all',
  PROSPECTS_ASSIGN: 'prospects.assign',
  PROSPECTS_DELETE: 'prospects.delete',
  PROSPECTS_CONVERT: 'prospects.convert',
  INTERACTIONS_CREATE: 'interactions.create',
  TASKS_MANAGE: 'tasks.manage',
  OPPORTUNITIES_MANAGE: 'opportunities.manage',
  QUOTES_MANAGE: 'quotes.manage',
  SALES_MANAGE: 'sales.manage',
  REPORTS_EXPORT: 'reports.export',
  IMPORT_RUN: 'import.run',
} as const

export type PermissionCode = (typeof P)[keyof typeof P] | (string & {})

/** La interfaz solo oculta acciones; el backend valida siempre cada permiso. */
export function usePermissions() {
  const permissions = useSessionStore((s) => s.user?.permissions)
  const set = new Set(permissions ?? [])
  return {
    can: (code: PermissionCode) => set.has(code),
    canAny: (...codes: PermissionCode[]) => codes.some((c) => set.has(c)),
  }
}

export function Can({ permission, children, fallback = null }: { permission: PermissionCode; children: ReactNode; fallback?: ReactNode }) {
  const { can } = usePermissions()
  return can(permission) ? children : fallback
}
