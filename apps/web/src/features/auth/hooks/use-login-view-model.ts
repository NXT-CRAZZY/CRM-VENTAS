import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useLocation, useNavigate } from 'react-router'
import { errorMessage } from '@/shared/api/errors'
import { useSessionStore } from '@/shared/auth/session-store'
import { authService } from '../api/auth-service'
import { type LoginForm, loginSchema } from '../model/schemas'

export function useLoginViewModel() {
  const navigate = useNavigate()
  const location = useLocation()
  const endedReason = useSessionStore((s) => s.endedReason)
  const form = useForm<LoginForm>({ resolver: zodResolver(loginSchema), defaultValues: { email: '', password: '' } })

  const mutation = useMutation({
    mutationFn: (data: LoginForm) => authService.login(data.email, data.password),
    onSuccess: () => {
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' ? from : '/', { replace: true })
    },
  })

  return {
    form,
    submit: form.handleSubmit((data) => mutation.mutate(data)),
    submitting: mutation.isPending,
    error: mutation.error ? errorMessage(mutation.error) : null,
    notice: endedReason === 'expired' ? 'Tu sesión expiró. Vuelve a ingresar para continuar.' : null,
  }
}
