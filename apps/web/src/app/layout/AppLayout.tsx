import { AnimatePresence, motion } from 'motion/react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { type PermissionCode, usePermissions } from '@/shared/auth/permissions'
import { useSessionStore } from '@/shared/auth/session-store'
import { ease } from '@/shared/lib/motion'
import { ForbiddenState } from '@/shared/ui/feedback'
import { Logo } from '@/shared/ui/misc'
import { MobileNav } from './MobileNav'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function SplashScreen() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background" aria-busy="true">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease }}
        className="flex flex-col items-center gap-5"
      >
        <Logo variant="mark" className="size-12" />
        <div className="h-0.5 w-24 overflow-hidden rounded-full bg-zinc-200">
          <div className="h-full w-1/2 animate-[shimmer_1.2s_infinite] bg-brand-600" />
        </div>
      </motion.div>
    </div>
  )
}

/** Protege las rutas privadas: sesión válida y contraseña definitiva. */
export function RequireAuth() {
  const { status, user } = useSessionStore()
  const location = useLocation()
  if (status === 'loading') return <SplashScreen />
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user?.must_change_password) return <Navigate to="/cambiar-clave" replace />
  return <Outlet />
}

export function RequirePermission({ permission }: { permission: PermissionCode | PermissionCode[] }) {
  const { can, canAny } = usePermissions()
  const allowed = Array.isArray(permission) ? canAny(...permission) : can(permission)
  return allowed ? <Outlet /> : <ForbiddenState />
}

export function RequireAnyPermission({ permissions }: { permissions: PermissionCode[] }) {
  const { canAny } = usePermissions()
  return canAny(...permissions) ? <Outlet /> : <ForbiddenState />
}

export function AppLayout() {
  const location = useLocation()
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 pb-24 lg:pb-0">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.16, ease }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
      <MobileNav />
    </div>
  )
}
