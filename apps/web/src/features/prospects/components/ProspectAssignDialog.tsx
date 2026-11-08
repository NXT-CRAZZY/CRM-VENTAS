import { useEffect, useState } from 'react'
import { useActiveUsers } from '@/features/admin/users/api/users-service'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '@/shared/ui/dialog'
import { Textarea } from '@/shared/ui/input'
import { FormField } from '@/shared/ui/page'
import { Select } from '@/shared/ui/menus'

export interface ProspectAssignDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title?: string
  description?: string
  confirmLabel?: string
  pending?: boolean
  onAssign: (values: { owner_id: string; reason: string | null }) => void
}

export function ProspectAssignDialog({
  open,
  onOpenChange,
  title = 'Asignar prospecto',
  description = 'Selecciona el nuevo responsable.',
  confirmLabel = 'Asignar',
  pending,
  onAssign,
}: ProspectAssignDialogProps) {
  const users = useActiveUsers(open)
  const [ownerId, setOwnerId] = useState('')
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (open) {
      setOwnerId('')
      setReason('')
    }
  }, [open])

  const options = users.data?.map((u) => ({ value: u.id, label: u.full_name })) ?? []
  const canSubmit = ownerId && !pending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader title={title} description={description} />
        <div className="space-y-4">
          <FormField label="Nuevo responsable" required>
            {() => (
              <Select
                value={ownerId}
                onValueChange={setOwnerId}
                placeholder="Seleccionar usuario…"
                options={options}
                disabled={pending}
              />
            )}
          </FormField>
          <FormField label="Motivo (opcional)">
            {(props) => (
              <Textarea
                {...props}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Ej. cambio de cartera, especialización…"
                disabled={pending}
                maxLength={500}
              />
            )}
          </FormField>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancelar
          </Button>
          <Button
            loading={pending}
            disabled={!canSubmit}
            onClick={() => onAssign({ owner_id: ownerId, reason: reason.trim() || null })}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
