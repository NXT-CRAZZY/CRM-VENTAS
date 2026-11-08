import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/shared/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
  {
    variants: {
      tone: {
        neutral: 'bg-zinc-100 text-zinc-700 ring-zinc-200',
        brand: 'bg-brand-50 text-brand-800 ring-brand-200',
        success: 'bg-success-soft text-green-800 ring-green-200',
        warning: 'bg-warning-soft text-amber-800 ring-amber-200',
        danger: 'bg-danger-soft text-red-800 ring-red-200',
        info: 'bg-info-soft text-blue-800 ring-blue-200',
        dark: 'bg-zinc-900 text-white ring-zinc-900',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

type BadgeProps = ComponentProps<'span'> & VariantProps<typeof badgeVariants> & { dot?: boolean }

export function Badge({ className, tone, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ tone }), className)} {...props}>
      {dot && <span className="size-1.5 rounded-full bg-current opacity-70" aria-hidden />}
      {children}
    </span>
  )
}

/** Badge con el color configurado en un catálogo (fondo traslúcido del mismo tono). */
export function ColorBadge({ color, children, className }: { color?: string | null; children: ReactNode; className?: string }) {
  if (!color) return <Badge className={className}>{children}</Badge>
  return (
    <span
      className={cn('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium', className)}
      style={{ backgroundColor: `${color}14`, color, boxShadow: `inset 0 0 0 1px ${color}33` }}
    >
      <span className="size-1.5 rounded-full" style={{ backgroundColor: color }} aria-hidden />
      {children}
    </span>
  )
}
