import { AlertCircle, Eye, EyeOff, Info } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { ease } from '@/shared/lib/motion'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { ThemeToggle } from '@/shared/theme/ThemeToggle'
import { Logo } from '@/shared/ui/misc'
import { FormField } from '@/shared/ui/page'
import { useLoginViewModel } from '../hooks/use-login-view-model'

export function LoginPage() {
  const vm = useLoginViewModel()
  const [showPassword, setShowPassword] = useState(false)
  const { errors } = vm.form.formState

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      {/* Panel de marca (solo escritorio) */}
      <div className="keep-zinc relative hidden overflow-hidden bg-ink-950 lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          className="pointer-events-none absolute -right-40 -top-40 size-[560px] rounded-full bg-brand-600/20 blur-3xl"
          aria-hidden
        />
        <div className="pointer-events-none absolute -bottom-48 -left-24 size-[420px] rounded-full bg-brand-500/10 blur-3xl" aria-hidden />
        <Logo onDark className="relative h-10 w-auto self-start" />
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease }}
          className="relative max-w-md"
        >
          <p className="text-3xl font-semibold leading-tight tracking-tight text-white">
            Cada prospecto con su estado, responsable y próxima acción.
          </p>
          <p className="mt-4 text-[15px] leading-relaxed text-zinc-400">
            El CRM comercial de DATA SERVICE: seguimiento, cotizaciones y ventas en un solo lugar.
          </p>
        </motion.div>
        <p className="relative text-xs text-zinc-500">© {new Date().getFullYear()} DATA SERVICE · DSCONT Software</p>
      </div>

      {/* Formulario */}
      <div className="relative flex items-center justify-center px-5 py-10 sm:px-8">
        <ThemeToggle className="absolute right-4 top-4" />
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease }}
          className="w-full max-w-sm"
        >
          <Logo className="mb-10 h-9 w-auto lg:hidden" />
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">Iniciar sesión</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Ingresa con tu correo corporativo.</p>

          {vm.notice && !vm.error && (
            <div className="mt-6 flex gap-2.5 rounded-lg border border-blue-100 bg-info-soft/60 p-3 text-sm text-blue-900">
              <Info className="mt-0.5 size-4 shrink-0" />
              {vm.notice}
            </div>
          )}
          {vm.error && (
            <div
              role="alert"
              className="mt-6 flex gap-2.5 rounded-lg border border-red-100 bg-danger-soft/60 p-3 text-sm text-red-800 animate-in fade-in-0 slide-in-from-top-1"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              {vm.error}
            </div>
          )}

          <form onSubmit={vm.submit} className="mt-6 space-y-4" noValidate>
            <FormField label="Correo" error={errors.email?.message}>
              {(p) => (
                <Input
                  {...p}
                  type="email"
                  autoComplete="username"
                  inputMode="email"
                  placeholder="nombre@dataservice.pe"
                  autoFocus
                  {...vm.form.register('email')}
                />
              )}
            </FormField>
            <FormField label="Contraseña" error={errors.password?.message}>
              {(p) => (
                <div className="relative">
                  <Input
                    {...p}
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    className="pr-10"
                    {...vm.form.register('password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-zinc-400 hover:text-zinc-700"
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
              )}
            </FormField>
            <Button type="submit" size="lg" className="w-full" loading={vm.submitting}>
              Ingresar
            </Button>
          </form>
          <p className="mt-8 text-center text-xs text-muted-foreground">
            ¿Olvidaste tu contraseña? Solicita al administrador que la restablezca.
          </p>
        </motion.div>
      </div>
    </div>
  )
}
