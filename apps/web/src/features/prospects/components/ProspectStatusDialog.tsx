import { useEffect, useState } from 'react'
import type { ProspectStatus } from '../api/prospects-service'
import { STATUS_CHANGE_OPTIONS } from '../model/constants'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '@/shared/ui/dialog'
import { Textarea } from '@/shared/ui/input'
import { FormField } from '@/shared/ui/page'
import { Select } from '@/shared/ui/menus'

export interface ProspectStatusDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentStatus?: ProspectStatus
  pending?: boolean
  onChange: (values: { status: ProspectStatus; reason: string }) => void
}

export function ProspectStatusDialog({
  open,
  onOpenChange,
  currentStatus,
  pending,
  onChange,
}: ProspectStatusDialogProps) {
  const [status, setStatus] = useState<ProspectStatus | ''>('')
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (open) {
      setStatus('')
      setReason('')
    }
  }, [open])

  const reasonOk = reason.trim().length >= 3
  const canSubmit = status && reasonOk && status !== currentStatus && !pending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader
          title="Cambiar estado"
          description="Registra el nuevo estado y el motivo del cambio."
        />
        <div className="space-y-4">
          <FormField label="Nuevo estado" required>
            {() => (
              <Select
                value={status}
                onValueChange={(v) => setStatus(v as ProspectStatus)}
                placeholder="Seleccionar estado…"
                options={STATUS_CHANGE_OPTIONS}
                disabled={pending}
              />
            )}
          </FormField>
          <FormField label="Motivo" required error={reason && !reasonOk ? 'Ingresa al menos 3 caracteres.' : undefined}>
            {(props) => (
              <Textarea
                {...props}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Ej. cliente solicitó pausar, no califica…"
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
            onClick={() => {
              if (!status) return
              onChange({ status, reason: reason.trim() })
            }}
          >
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
