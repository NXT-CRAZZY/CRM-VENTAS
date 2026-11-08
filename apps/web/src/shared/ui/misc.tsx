import { motion } from 'motion/react'
import { type ReactNode, useState } from 'react'
import isotipo from '@/assets/brand/isotipo.png'
import isotipoLight from '@/assets/brand/isotipo-light.png'
import logo from '@/assets/brand/logo.png'
import logoLight from '@/assets/brand/logo-light.png'
import { fadeUp } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Button } from './button'
import { Dialog, DialogContent, DialogFooter, DialogHeader } from './dialog'

export function Logo({ variant = 'full', onDark, className }: { variant?: 'full' | 'mark'; onDark?: boolean; className?: string }) {
  const src = variant === 'full' ? (onDark ? logoLight : logo) : onDark ? isotipoLight : isotipo
  return <img src={src} alt="DSCONT Software" className={cn('select-none', className)} draggable={false} />
}

export function KpiCard({
  label,
  value,
  hint,
  icon,
  accent,
}: {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  accent?: boolean
}) {
  return (
    <motion.div
      variants={fadeUp}
      className={cn(
        'group relative overflow-hidden rounded-lg border bg-card p-4 shadow-xs transition-shadow duration-200 hover:shadow-md sm:p-5',
        accent ? 'border-brand-200/70' : 'border-zinc-200/80',
      )}
    >
      {accent && <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-brand-600 to-brand-400" />}
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] font-medium text-zinc-500">{label}</p>
        {icon && (
          <span className="rounded-md bg-zinc-50 p-1.5 text-zinc-400 ring-1 ring-inset ring-zinc-100 transition-colors group-hover:text-brand-600 [&_svg]:size-4">
            {icon}
          </span>
        )}
      </div>
      <p className="tabular mt-2 text-2xl font-semibold tracking-tight text-zinc-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </motion.div>
  )
}

/** Confirmación solo para acciones destructivas o irreversibles. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirmar',
  destructive,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  description?: ReactNode
  confirmLabel?: string
  destructive?: boolean
  onConfirm: () => Promise<unknown> | void
}) {
  const [busy, setBusy] = useState(false)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" hideClose>
        <DialogHeader title={title} description={description} />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancelar
          </Button>
          <Button
            variant={destructive ? 'destructive' : 'primary'}
            loading={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await onConfirm()
                onOpenChange(false)
              } finally {
                setBusy(false)
              }
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export const COLOR_SWATCHES = [
  '#E03E0F', '#DC2626', '#D97706', '#CA8A04', '#16A34A', '#0D9488',
  '#0891B2', '#2563EB', '#7C3AED', '#DB2777', '#71717A', '#18181B',
]

export function ColorPicker({ value, onChange }: { value?: string | null; onChange: (color: string | null) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {COLOR_SWATCHES.map((c) => {
        const active = value?.toUpperCase() === c
        return (
          <button
            key={c}
            type="button"
            onClick={() => onChange(active ? null : c)}
            className={cn(
              'size-8 rounded-full ring-offset-2 transition-transform duration-150 hover:scale-110 sm:size-7',
              active && 'ring-2 ring-zinc-900',
            )}
            style={{ backgroundColor: c }}
            aria-label={`Color ${c}`}
            aria-pressed={active}
          />
        )
      })}
    </div>
  )
}
