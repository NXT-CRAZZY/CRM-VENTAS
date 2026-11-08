import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { handleFormError } from '@/shared/lib/forms'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '@/shared/ui/dialog'
import { Input, Textarea } from '@/shared/ui/input'
import { FormField } from '@/shared/ui/page'
import { type Role, rolesService } from '../api/roles-service'

const schema = z.object({
  name: z.string().trim().min(2, 'Ingresa un nombre.').max(80),
  description: z.string().trim().max(500).optional(),
})
type Form = z.infer<typeof schema>

export function CreateRoleDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (role: Role) => void
}) {
  const form = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { name: '', description: '' } })
  useEffect(() => {
    if (open) form.reset({ name: '', description: '' })
  }, [open, form])

  const create = useMutation({
    mutationFn: (d: Form) => rolesService.create({ name: d.name, description: d.description || null, permissions: [] }),
    onSuccess: (role) => {
      toast.success(`Rol “${role.name}” creado`, { description: 'Ahora marca los permisos que tendrá.' })
      onCreated(role)
      onOpenChange(false)
    },
    onError: (e) => handleFormError(form, e, { ROLE_NAME_TAKEN: 'name' }),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader title="Nuevo rol" description="Por ejemplo: Supervisora de ventas, Asistente comercial." />
        <form id="role-form" onSubmit={form.handleSubmit((d) => create.mutate(d))} className="space-y-4" noValidate>
          <FormField label="Nombre" required error={form.formState.errors.name?.message}>
            {(p) => <Input {...p} autoFocus {...form.register('name')} />}
          </FormField>
          <FormField label="Descripción" optional>
            {(p) => <Textarea {...p} rows={2} {...form.register('description')} />}
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" form="role-form" loading={create.isPending}>Crear rol</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
