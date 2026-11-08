import type { ComponentProps } from 'react'
import { cn } from '@/shared/lib/utils'

export const fieldBase =
  'w-full rounded-md border border-input bg-card px-3 text-sm text-foreground shadow-xs transition-[border-color,box-shadow] duration-150 placeholder:text-zinc-400 hover:border-zinc-300 focus-visible:border-brand-500 focus-visible:ring-3 focus-visible:ring-brand-500/15 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:opacity-60 aria-invalid:border-danger aria-invalid:ring-danger/15'

/** h-11 en móvil (área táctil cómoda), h-9 en escritorio. */
export function Input({ className, ...props }: ComponentProps<'input'>) {
  return <input className={cn(fieldBase, 'h-11 sm:h-9', className)} {...props} />
}

export function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return <textarea className={cn(fieldBase, 'min-h-20 py-2', className)} {...props} />
}

export function Label({ className, ...props }: ComponentProps<'label'>) {
  return <label className={cn('text-[13px] font-medium text-zinc-700', className)} {...props} />
}
