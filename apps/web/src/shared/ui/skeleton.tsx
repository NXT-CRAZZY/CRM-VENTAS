import type { ComponentProps } from 'react'
import { cn } from '@/shared/lib/utils'

export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div className={cn('relative overflow-hidden rounded-md bg-zinc-100', className)} aria-hidden {...props}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/70 to-transparent" />
    </div>
  )
}
