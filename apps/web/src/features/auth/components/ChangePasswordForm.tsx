import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { ApiError, errorMessage } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { FormField } from '@/shared/ui/page'
import { authService } from '../api/auth-service'
import { type ChangePasswordForm as Form, changePasswordSchema } from '../model/schemas'

export function ChangePasswordForm({ onDone, submitLabel = 'Guardar contraseña' }: { onDone?: () => void; submitLabel?: string }) {
  const form = useForm<Form>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: '', new_password: '', confirm: '' },
  })
  const { errors } = form.formState

  const mutation = useMutation({
    mutationFn: (d: Form) => authService.changePassword({ current_password: d.current_password, new_password: d.new_password }),
    onSuccess: () => {
      toast.success('Contraseña actualizada')
      form.reset()
      onDone?.()
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === 'WRONG_PASSWORD') {
        form.setError('current_password', { message: e.message })
      } else {
        toast.error(errorMessage(e))
      }
    },
  })

  return (
    <form onSubmit={form.handleSubmit((d) => mutation.mutate(d))} className="space-y-4" noValidate>
      <FormField label="Contraseña actual" error={errors.current_password?.message}>
        {(p) => <Input {...p} type="password" autoComplete="current-password" {...form.register('current_password')} />}
      </FormField>
      <FormField
        label="Nueva contraseña"
        hint="Mínimo 8 caracteres, con letras y números."
        error={errors.new_password?.message}
      >
        {(p) => <Input {...p} type="password" autoComplete="new-password" {...form.register('new_password')} />}
      </FormField>
      <FormField label="Repite la nueva contraseña" error={errors.confirm?.message}>
        {(p) => <Input {...p} type="password" autoComplete="new-password" {...form.register('confirm')} />}
      </FormField>
      <Button type="submit" className="w-full sm:w-auto" loading={mutation.isPending}>
        {submitLabel}
      </Button>
    </form>
  )
}
