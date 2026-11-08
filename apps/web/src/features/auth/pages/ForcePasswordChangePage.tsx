import { ShieldCheck } from 'lucide-react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router'
import { useSessionStore } from '@/shared/auth/session-store'
import { ease } from '@/shared/lib/motion'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Logo } from '@/shared/ui/misc'
import { authService } from '../api/auth-service'
import { ChangePasswordForm } from '../components/ChangePasswordForm'

/** Primer ingreso o clave restablecida: el usuario debe definir su propia contraseña. */
export function ForcePasswordChangePage() {
  const navigate = useNavigate()
  const user = useSessionStore((s) => s.user)
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-5 py-10">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease }} className="w-full max-w-md">
        <Logo className="mx-auto mb-8 h-8 w-auto" />
        <Card className="p-6 sm:p-8">
          <div className="mb-6 flex items-start gap-3">
            <span className="rounded-lg bg-brand-50 p-2 text-brand-600 ring-1 ring-inset ring-brand-100">
              <ShieldCheck className="size-5" />
            </span>
            <div>
              <h1 className="text-lg font-semibold text-zinc-900">Crea tu contraseña</h1>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Hola {user?.full_name.split(' ')[0]}, por seguridad reemplaza la contraseña temporal antes de continuar.
              </p>
            </div>
          </div>
          <ChangePasswordForm submitLabel="Guardar y continuar" onDone={() => navigate('/', { replace: true })} />
        </Card>
        <Button variant="link" className="mx-auto mt-4 flex text-zinc-500" onClick={() => authService.logout()}>
          Cerrar sesión
        </Button>
      </motion.div>
    </div>
  )
}
