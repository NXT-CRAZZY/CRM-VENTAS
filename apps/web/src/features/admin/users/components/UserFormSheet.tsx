import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Copy, KeyRound, Wand2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { useRoles } from '@/features/admin/roles/api/roles-service'
import { passwordRule } from '@/features/auth/model/schemas'
import { errorMessage } from '@/shared/api/errors'
import { generateTempPassword, handleFormError } from '@/shared/lib/forms'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Checkbox } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'
import { type User, usersService } from '../api/users-service'

const baseSchema = z.object({
  full_name: z.string().trim().min(3, 'Ingresa el nombre completo.'),
  email: z.string().trim().email('Ingresa un correo válido.'),
  phone: z.string().trim().max(30).optional(),
  role_ids: z.array(z.string()).min(1, 'Selecciona al menos un rol.'),
  password: z.string().optional(),
})
type Form = z.infer<typeof baseSchema>

const createSchema = baseSchema.extend({ password: passwordRule })

export function UserFormSheet({ user, onClose, onSaved }: { user: User | 'new' | null; onClose: () => void; onSaved: () => void }) {
  const isNew = user === 'new'
  const editing = user && user !== 'new' ? user : null
  const roles = useRoles()
  const [issuedPassword, setIssuedPassword] = useState<string | null>(null)

  const form = useForm<Form>({ resolver: zodResolver(isNew ? createSchema : baseSchema) })
  const { errors } = form.formState

  useEffect(() => {
    if (!user) return
    setIssuedPassword(null)
    form.reset(
      editing
        ? { full_name: editing.full_name, email: editing.email, phone: editing.phone ?? '', role_ids: editing.roles.map((r) => r.id) }
        : { full_name: '', email: '', phone: '', role_ids: [], password: generateTempPassword() },
    )
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: (d: Form) =>
      editing
        ? usersService.update(editing.id, { full_name: d.full_name, email: d.email, phone: d.phone || null, role_ids: d.role_ids })
        : usersService.create({ full_name: d.full_name, email: d.email, phone: d.phone || null, role_ids: d.role_ids, password: d.password! }),
    onSuccess: (saved, d) => {
      onSaved()
      if (isNew) {
        toast.success(`Usuario ${saved.full_name} creado`, { description: `Contraseña temporal: ${d.password}` })
      } else {
        toast.success('Cambios guardados')
      }
      onClose()
    },
    onError: (e) => handleFormError(form, e, { EMAIL_TAKEN: 'email' }),
  })

  const reset = useMutation({
    mutationFn: (password: string) => usersService.resetPassword(editing!.id, password).then(() => password),
    onSuccess: (password) => {
      setIssuedPassword(password)
      toast.success('Contraseña restablecida. Sus sesiones activas se cerraron.')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
    <Sheet open={!!user} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={isNew ? 'Nuevo usuario' : 'Editar usuario'}
        description={isNew ? 'Deberá cambiar la contraseña temporal en su primer ingreso.' : editing?.email}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" form="user-form" loading={save.isPending}>
              {isNew ? 'Crear usuario' : 'Guardar cambios'}
            </Button>
          </>
        }
      >
        <form id="user-form" onSubmit={form.handleSubmit((d) => save.mutate(d))} className="space-y-5" noValidate>
          <FormField label="Nombre completo" required error={errors.full_name?.message}>
            {(p) => <Input {...p} autoComplete="off" placeholder="Ej. María Quispe Huamán" {...form.register('full_name')} />}
          </FormField>
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Correo" required error={errors.email?.message}>
              {(p) => <Input {...p} type="email" inputMode="email" autoComplete="off" {...form.register('email')} />}
            </FormField>
            <FormField label="Teléfono" optional error={errors.phone?.message}>
              {(p) => <Input {...p} type="tel" inputMode="tel" {...form.register('phone')} />}
            </FormField>
          </div>

          <FormField label="Rol" required error={errors.role_ids?.message} hint="Define qué puede ver y hacer en el CRM.">
            {() => (
              <Controller
                control={form.control}
                name="role_ids"
                render={({ field }) => (
                  <div className="grid gap-2">
                    {roles.data?.map((role) => {
                      const checked = field.value?.includes(role.id) ?? false
                      return (
                        <label
                          key={role.id}
                          className={cn(
                            'flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors',
                            checked ? 'border-brand-300 bg-brand-50/50' : 'border-zinc-200 hover:bg-zinc-50',
                          )}
                        >
                          <Checkbox
                            className="mt-0.5"
                            checked={checked}
                            onCheckedChange={(v) =>
                              field.onChange(v ? [...(field.value ?? []), role.id] : field.value.filter((id) => id !== role.id))
                            }
                          />
                          <span>
                            <span className="block text-sm font-medium text-zinc-900">{role.name}</span>
                            {role.description && <span className="block text-xs text-muted-foreground">{role.description}</span>}
                          </span>
                        </label>
                      )
                    })}
                  </div>
                )}
              />
            )}
          </FormField>

          {isNew && (
            <FormField
              label="Contraseña temporal"
              required
              error={errors.password?.message}
              hint="Compártela con el usuario por un medio seguro."
            >
              {(p) => (
                <div className="flex gap-2">
                  <Input {...p} className="font-mono" autoComplete="off" {...form.register('password')} />
                  <Button type="button" variant="outline" size="icon" aria-label="Generar otra" onClick={() => form.setValue('password', generateTempPassword())}>
                    <Wand2 />
                  </Button>
                </div>
              )}
            </FormField>
          )}
        </form>

        {editing && (
          <div className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50/60 p-4">
            <p className="flex items-center gap-2 text-sm font-medium text-zinc-900">
              <KeyRound className="size-4 text-zinc-400" /> Restablecer contraseña
            </p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Genera una contraseña temporal; el usuario deberá cambiarla al ingresar.
            </p>
            {issuedPassword ? (
              <div className="mt-3 flex items-center gap-2 rounded-md border border-brand-200 bg-card px-3 py-2">
                <code className="flex-1 font-mono text-sm text-zinc-900">{issuedPassword}</code>
                <Button
                  size="icon-sm"
                  variant="ghost"
                  aria-label="Copiar"
                  onClick={() => navigator.clipboard.writeText(issuedPassword).then(() => toast.success('Copiada'))}
                >
                  <Copy />
                </Button>
              </div>
            ) : (
              <Button className="mt-3" variant="outline" size="sm" loading={reset.isPending} onClick={() => reset.mutate(generateTempPassword())}>
                Generar contraseña temporal
              </Button>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
