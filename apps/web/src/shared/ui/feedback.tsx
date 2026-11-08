import { AlertTriangle, Inbox, Lock, SearchX } from 'lucide-react'
import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { errorMessage } from '@/shared/api/errors'
import { fadeUp } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Button } from './button'

function StateShell({
  icon,
  title,
  description,
  action,
  tone = 'neutral',
  className,
}: {
  icon: ReactNode
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  tone?: 'neutral' | 'danger' | 'brand'
  className?: string
}) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="show"
      className={cn('flex flex-col items-center justify-center px-6 py-14 text-center', className)}
    >
      <div
        className={cn(
          'mb-4 flex size-12 items-center justify-center rounded-xl ring-1 ring-inset [&_svg]:size-5',
          tone === 'danger' && 'bg-red-50 text-red-600 ring-red-100',
          tone === 'brand' && 'bg-brand-50 text-brand-600 ring-brand-100',
          tone === 'neutral' && 'bg-zinc-50 text-zinc-400 ring-zinc-200/70',
        )}
      >
        {icon}
      </div>
      <p className="text-[15px] font-semibold text-zinc-900">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </motion.div>
  )
}

export function EmptyState(props: { title: ReactNode; description?: ReactNode; action?: ReactNode; icon?: ReactNode; className?: string }) {
  return <StateShell icon={props.icon ?? <Inbox />} tone="brand" {...props} />
}

export function NoResults({ onClear }: { onClear?: () => void }) {
  return (
    <StateShell
      icon={<SearchX />}
      title="Sin resultados"
      description="No encontramos registros con esos filtros."
      action={onClear && (
        <Button variant="outline" size="sm" onClick={onClear}>
          Limpiar filtros
        </Button>
      )}
    />
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <StateShell
      icon={<AlertTriangle />}
      tone="danger"
      title="No pudimos cargar la información"
      description={errorMessage(error)}
      action={onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    />
  )
}

export function ForbiddenState() {
  return (
    <StateShell
      icon={<Lock />}
      title="Sin acceso"
      description="Tu rol no tiene permiso para ver esta sección. Si lo necesitas, consulta con el administrador."
    />
  )
}
