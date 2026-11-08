import { X } from 'lucide-react'
import { Dialog as D } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { useIsDesktop } from '@/shared/hooks/use-media-query'
import { cn } from '@/shared/lib/utils'
import { overlayClass } from './dialog'

export const Sheet = D.Root
export const SheetTrigger = D.Trigger
export const SheetClose = D.Close

const sides = {
  right:
    'inset-y-0 right-0 h-dvh w-full max-w-md border-l data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right',
  left: 'inset-y-0 left-0 h-dvh w-72 border-r data-[state=open]:slide-in-from-left data-[state=closed]:slide-out-to-left',
  bottom:
    'inset-x-0 bottom-0 max-h-[92dvh] rounded-t-2xl border-t data-[state=open]:slide-in-from-bottom data-[state=closed]:slide-out-to-bottom',
}

/**
 * Panel lateral. Por defecto es responsivo: panel derecho en escritorio y
 * "bottom sheet" en celular, para formularios cómodos con el pulgar.
 */
export function SheetContent({
  className,
  children,
  side,
  title,
  description,
  footer,
  ...props
}: Omit<ComponentProps<typeof D.Content>, 'title'> & {
  side?: keyof typeof sides
  title?: ReactNode
  description?: ReactNode
  footer?: ReactNode
}) {
  const isDesktop = useIsDesktop()
  const resolved = side ?? (isDesktop ? 'right' : 'bottom')
  return (
    <D.Portal>
      <D.Overlay className={overlayClass} />
      <D.Content
        className={cn(
          'fixed z-50 flex flex-col border-zinc-200/80 bg-card shadow-lg duration-250 ease-out data-[state=open]:animate-in data-[state=closed]:animate-out',
          sides[resolved],
          className,
        )}
        {...props}
      >
        {resolved === 'bottom' && <div className="mx-auto mt-2 h-1 w-10 shrink-0 rounded-full bg-zinc-300" aria-hidden />}
        {title !== undefined && (
          <div className="flex items-start justify-between gap-4 border-b border-zinc-100 px-5 py-4">
            <div className="min-w-0 space-y-0.5">
              <D.Title className="truncate text-base font-semibold text-zinc-900">{title}</D.Title>
              <D.Description className={cn('text-[13px] text-muted-foreground', !description && 'sr-only')}>
                {description ?? title}
              </D.Description>
            </div>
            <D.Close className="-mr-1 rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700">
              <X className="size-4" />
              <span className="sr-only">Cerrar</span>
            </D.Close>
          </div>
        )}
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && (
          <div className="pb-safe flex flex-col-reverse gap-2 border-t border-zinc-100 bg-zinc-50/60 px-5 py-3 sm:flex-row sm:justify-end">
            {footer}
          </div>
        )}
      </D.Content>
    </D.Portal>
  )
}
