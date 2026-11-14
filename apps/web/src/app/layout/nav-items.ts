import {
  BarChart3,
  Bell,
  ClipboardList,
  FileText,
  History,
  KanbanSquare,
  LayoutDashboard,
  ListChecks,
  type LucideIcon,
  Package,
  Settings2,
  ShieldCheck,
  TrendingUp,
  Users,
  UsersRound,
} from 'lucide-react'
import { P, type PermissionCode } from '@/shared/auth/permissions'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  permission?: PermissionCode | PermissionCode[]
  /** Módulos planificados en fases siguientes: se muestran deshabilitados. */
  soon?: string
  /** Aparece en la barra inferior del celular. */
  mobile?: boolean
}

export interface NavSection {
  title?: string
  items: NavItem[]
}

export const NAV: NavSection[] = [
  {
    items: [
      { label: 'Inicio', to: '/', icon: LayoutDashboard, mobile: true },
      { label: 'Prospectos', to: '/prospectos', icon: UsersRound, permission: [P.PROSPECTS_READ_OWN, P.PROSPECTS_READ_ALL], mobile: true },
      { label: 'Tareas', to: '/tareas', icon: ListChecks, permission: P.TASKS_MANAGE },
      { label: 'Pipeline', to: '/pipeline', icon: KanbanSquare, permission: P.OPPORTUNITIES_MANAGE },
      { label: 'Cotizaciones', to: '/cotizaciones', icon: FileText, permission: P.QUOTES_MANAGE },
      { label: 'Informe de ventas', to: '/informe-semanal', icon: BarChart3, permission: P.IMPORT_RUN },
      { label: 'Alertas', to: '/alertas', icon: Bell },
      { label: 'Dashboard gerencial', to: '/dashboard/gerencial', icon: TrendingUp, permission: P.DASHBOARD_MANAGEMENT },
    ],
  },
  {
    title: 'Catálogo',
    items: [{ label: 'Productos', to: '/productos', icon: Package, permission: P.PRODUCTS_READ, mobile: true }],
  },
  {
    title: 'Administración',
    items: [
      { label: 'Usuarios', to: '/admin/usuarios', icon: Users, permission: P.USERS_READ },
      { label: 'Roles y permisos', to: '/admin/roles', icon: ShieldCheck, permission: P.ROLES_READ },
      { label: 'Catálogos', to: '/admin/catalogos', icon: ClipboardList, permission: P.CATALOGS_MANAGE },
      { label: 'Configuración', to: '/admin/configuracion', icon: Settings2, permission: P.SETTINGS_READ },
      { label: 'Auditoría', to: '/admin/auditoria', icon: History, permission: P.AUDIT_READ },
    ],
  },
]

function allowed(item: NavItem, can: (code: PermissionCode) => boolean): boolean {
  if (!item.permission) return true
  const codes = Array.isArray(item.permission) ? item.permission : [item.permission]
  return codes.some(can)
}

export function visibleNav(can: (code: PermissionCode) => boolean): NavSection[] {
  return NAV.map((s) => ({ ...s, items: s.items.filter((i) => allowed(i, can)) })).filter(
    (s) => s.items.length > 0,
  )
}
