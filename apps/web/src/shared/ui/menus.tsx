import { Check, ChevronDown } from 'lucide-react'
import { Checkbox as CB, DropdownMenu as DM, Select as S, Switch as SW, Tooltip as T } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/shared/lib/utils'
import { fieldBase } from './input'

const popoverAnim =
  'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.97] data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[side=bottom]:slide-in-from-top-1 data-[side=top]:slide-in-from-bottom-1 duration-150'

/* ---------- Dropdown ---------- */
export const DropdownMenu = DM.Root
export const DropdownMenuTrigger = DM.Trigger

export function DropdownMenuContent({ className, sideOffset = 6, ...props }: ComponentProps<typeof DM.Content>) {
  return (
    <DM.Portal>
      <DM.Content
        sideOffset={sideOffset}
        className={cn(
          'z-50 min-w-48 overflow-hidden rounded-lg border border-zinc-200/80 bg-popover p-1 shadow-md',
          popoverAnim,
          className,
        )}
        {...props}
      />
    </DM.Portal>
  )
}

export function DropdownMenuItem({
  className,
  destructive,
  ...props
}: ComponentProps<typeof DM.Item> & { destructive?: boolean }) {
  return (
    <DM.Item
      className={cn(
        'flex cursor-pointer select-none items-center gap-2 rounded-md px-2.5 py-2 text-sm text-zinc-700 outline-none transition-colors data-[disabled]:pointer-events-none data-[highlighted]:bg-zinc-100 data-[highlighted]:text-zinc-900 data-[disabled]:opacity-50 [&_svg]:size-4 [&_svg]:text-zinc-400',
        destructive && 'text-red-700 data-[highlighted]:bg-red-50 data-[highlighted]:text-red-800 [&_svg]:text-red-500',
        className,
      )}
      {...props}
    />
  )
}

export function DropdownMenuLabel({ className, ...props }: ComponentProps<typeof DM.Label>) {
  return <DM.Label className={cn('px-2.5 py-1.5 text-xs font-medium text-zinc-500', className)} {...props} />
}

export function DropdownMenuSeparator() {
  return <DM.Separator className="-mx-1 my-1 h-px bg-zinc-100" />
}

/* ---------- Select ---------- */
export interface SelectOption {
  value: string
  label: ReactNode
}

export function Select({
  value,
  onValueChange,
  options,
  placeholder = 'Selecciona…',
  className,
  disabled,
  id,
  'aria-invalid': ariaInvalid,
}: {
  value?: string
  onValueChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  className?: string
  disabled?: boolean
  id?: string
  'aria-invalid'?: boolean
}) {
  return (
    <S.Root value={value} onValueChange={onValueChange} disabled={disabled}>
      <S.Trigger
        id={id}
        aria-invalid={ariaInvalid}
        className={cn(fieldBase, 'flex h-11 items-center justify-between gap-2 text-left sm:h-9 data-[placeholder]:text-zinc-400', className)}
      >
        <S.Value placeholder={placeholder} />
        <S.Icon>
          <ChevronDown className="size-4 text-zinc-400" />
        </S.Icon>
      </S.Trigger>
      <S.Portal>
        <S.Content
          position="popper"
          sideOffset={6}
          className={cn(
            'z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-lg border border-zinc-200/80 bg-popover shadow-md',
            popoverAnim,
          )}
        >
          <S.Viewport className="p-1">
            {options.map((o) => (
              <S.Item
                key={o.value}
                value={o.value}
                className="relative flex cursor-pointer select-none items-center rounded-md py-2 pl-8 pr-3 text-sm text-zinc-700 outline-none data-[highlighted]:bg-zinc-100 data-[highlighted]:text-zinc-900"
              >
                <S.ItemIndicator className="absolute left-2.5">
                  <Check className="size-4 text-brand-600" />
                </S.ItemIndicator>
                <S.ItemText>{o.label}</S.ItemText>
              </S.Item>
            ))}
          </S.Viewport>
        </S.Content>
      </S.Portal>
    </S.Root>
  )
}

/* ---------- Switch / Checkbox ---------- */
export function Switch({ className, ...props }: ComponentProps<typeof SW.Root>) {
  return (
    <SW.Root
      className={cn(
        'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full bg-zinc-300 p-0.5 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary',
        className,
      )}
      {...props}
    >
      <SW.Thumb className="block size-4 rounded-full bg-white shadow-sm transition-transform duration-200 ease-out data-[state=checked]:translate-x-4" />
    </SW.Root>
  )
}

export function Checkbox({ className, ...props }: ComponentProps<typeof CB.Root>) {
  return (
    <CB.Root
      className={cn(
        'peer flex size-4.5 shrink-0 items-center justify-center rounded-[5px] border border-zinc-300 bg-white shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary',
        className,
      )}
      {...props}
    >
      <CB.Indicator className="text-white data-[state=checked]:animate-in data-[state=checked]:zoom-in-75">
        <Check className="size-3.5" strokeWidth={3} />
      </CB.Indicator>
    </CB.Root>
  )
}

/* ---------- Tooltip ---------- */
export const TooltipProvider = T.Provider

export function Tooltip({ content, children, side = 'top' }: { content: ReactNode; children: ReactNode; side?: 'top' | 'right' | 'bottom' | 'left' }) {
  return (
    <T.Root>
      <T.Trigger asChild>{children}</T.Trigger>
      <T.Portal>
        <T.Content
          side={side}
          sideOffset={6}
          className={cn('z-50 rounded-md bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-white shadow-md', popoverAnim)}
        >
          {content}
        </T.Content>
      </T.Portal>
    </T.Root>
  )
}
