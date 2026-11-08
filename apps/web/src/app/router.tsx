import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, Outlet } from 'react-router'
import { ForcePasswordChangePage } from '@/features/auth/pages/ForcePasswordChangePage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { P } from '@/shared/auth/permissions'
import { useSessionStore } from '@/shared/auth/session-store'
import { DataListSkeleton } from '@/shared/ui/data-list'
import { AppLayout, RequireAuth, RequirePermission, SplashScreen } from './layout/AppLayout'

// Las pantallas de administración se cargan bajo demanda (no pesan en el primer ingreso).
const UsersPage = lazy(() => import('@/features/admin/users/pages/UsersPage'))
const RolesPage = lazy(() => import('@/features/admin/roles/pages/RolesPage'))
const CatalogsPage = lazy(() => import('@/features/admin/catalogs/pages/CatalogsPage'))
const ProductsPage = lazy(() => import('@/features/products/pages/ProductsPage'))
const ProspectsPage = lazy(() => import('@/features/prospects/pages/ProspectsPage'))
const ProspectDetailPage = lazy(() => import('@/features/prospects/pages/ProspectDetailPage'))
const TasksPage = lazy(() => import('@/features/tasks/pages/TasksPage'))
const PipelinePage = lazy(() => import('@/features/opportunities/pages/PipelinePage'))
const QuotesPage = lazy(() => import('@/features/quotes/pages/QuotesPage'))
// const ImportsPage = lazy(() => import('@/features/imports/pages/ImportsPage'))
const WeeklyReportPage = lazy(() => import('@/features/imports/pages/WeeklyReportPage'))
const SettingsPage = lazy(() => import('@/features/admin/settings/pages/SettingsPage'))
const AuditPage = lazy(() => import('@/features/admin/audit/pages/AuditPage'))
const AlertsPage = lazy(() => import('@/features/alerts/pages/AlertsPage'))
const ManagementDashboardPage = lazy(() => import('@/features/dashboard/pages/ManagementDashboardPage'))
const DesignSystemPage = lazy(() => import('@/features/design-system/DesignSystemPage'))

function Lazy() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl p-8"><DataListSkeleton /></div>}>
      <Outlet />
    </Suspense>
  )
}

function PublicOnly() {
  const status = useSessionStore((s) => s.status)
  if (status === 'loading') return <SplashScreen />
  return status === 'authenticated' ? <Navigate to="/" replace /> : <Outlet />
}

function PasswordGate() {
  const { status, user } = useSessionStore()
  if (status === 'loading') return <SplashScreen />
  if (status === 'anonymous') return <Navigate to="/login" replace />
  return user?.must_change_password ? <Outlet /> : <Navigate to="/" replace />
}

export const router = createBrowserRouter([
  { element: <PublicOnly />, children: [{ path: '/login', element: <LoginPage /> }] },
  { element: <PasswordGate />, children: [{ path: '/cambiar-clave', element: <ForcePasswordChangePage /> }] },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          {
            element: <Lazy />,
            children: [
              { element: <RequirePermission permission={P.PRODUCTS_READ} />, children: [{ path: 'productos', element: <ProductsPage /> }] },
              {
                element: <RequirePermission permission={[P.PROSPECTS_READ_OWN, P.PROSPECTS_READ_ALL]} />,
                children: [
                  { path: 'prospectos', element: <ProspectsPage /> },
                  { path: 'prospectos/:id', element: <ProspectDetailPage /> },
                ],
              },
              {
                element: <RequirePermission permission={P.TASKS_MANAGE} />,
                children: [{ path: 'tareas', element: <TasksPage /> }],
              },
              {
                element: <RequirePermission permission={P.OPPORTUNITIES_MANAGE} />,
                children: [{ path: 'pipeline', element: <PipelinePage /> }],
              },
              {
                element: <RequirePermission permission={P.QUOTES_MANAGE} />,
                children: [{ path: 'cotizaciones', element: <QuotesPage /> }],
              },
              {
                element: <RequirePermission permission={P.IMPORT_RUN} />,
                children: [{ path: 'informe-semanal', element: <WeeklyReportPage /> }],
              },
              { path: 'alertas', element: <AlertsPage /> },
              {
                element: <RequirePermission permission={P.DASHBOARD_MANAGEMENT} />,
                children: [{ path: 'dashboard/gerencial', element: <ManagementDashboardPage /> }],
              },
              {
                path: 'admin',
                children: [
                  { element: <RequirePermission permission={P.USERS_READ} />, children: [{ path: 'usuarios', element: <UsersPage /> }] },
                  { element: <RequirePermission permission={P.ROLES_READ} />, children: [{ path: 'roles', element: <RolesPage /> }] },
                  {
                    element: <RequirePermission permission={P.CATALOGS_MANAGE} />,
                    children: [{ path: 'catalogos', element: <CatalogsPage /> }],
                  },
                  {
                    element: <RequirePermission permission={P.SETTINGS_READ} />,
                    children: [{ path: 'configuracion', element: <SettingsPage /> }],
                  },
                  { element: <RequirePermission permission={P.AUDIT_READ} />, children: [{ path: 'auditoria', element: <AuditPage /> }] },
                ],
              },
              ...(import.meta.env.DEV ? [{ path: 'design-system', element: <DesignSystemPage /> }] : []),
            ],
          },
          { path: '*', element: <Navigate to="/" replace /> },
        ],
      },
    ],
  },
])
