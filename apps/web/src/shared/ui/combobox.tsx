import { Check, ChevronDown, Search } from 'lucide-react'
import { Popover as PO } from 'radix-ui'
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from '@/shared/lib/utils'
import { fieldBase } from './input'

export interface ComboboxOption {
  value: string
  /** Texto que se muestra en la lista y en el campo. */
  label: ReactNode
  /** Texto contra el que se filtra (nombre, código…). */
  searchText: string
}

const normalize = (s: string) =>
  s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

/** Selector con buscador: escribe para filtrar las opciones (todas las palabras deben coincidir). */
export function Combobox({
  value,
  onValueChange,
  options,
  placeholder = 'Selecciona…',
  searchPlaceholder = 'Buscar…',
  emptyText = 'Sin resultados',
  className,
  disabled,
  id,
}: {
  value?: string
  onValueChange: (value: string) => void
  options: ComboboxOption[]
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  className?: string
  disabled?: boolean
  id?: string
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)

  const selected = options.find((o) => o.value === value)

  const filtered = useMemo(() => {
    const words = normalize(query).split(/\s+/).filter(Boolean)
    if (words.length === 0) return options
    return options.filter((o) => {
      const hay = normalize(o.searchText)
      return words.every((w) => hay.includes(w))
    })
  }, [options, query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setActive(Math.max(0, options.findIndex((o) => o.value === value)))
    }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => setActive(0), [query])

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [active])

  const pick = (o: ComboboxOption) => {
    onValueChange(o.value)
    setOpen(false)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const o = filtered[active]
      if (o) pick(o)
    }
  }

  return (
    <PO.Root open={open} onOpenChange={setOpen}>
      <PO.Trigger asChild>
        <button
          id={id}
          type="button"
          disabled={disabled}
          className={cn(fieldBase, 'flex h-auto min-h-11 items-center justify-between gap-2 py-2 text-left sm:min-h-9', className)}
        >
          <span className={cn('min-w-0 flex-1 break-words', !selected && 'text-zinc-400')}>{selected ? selected.label : placeholder}</span>
          <ChevronDown className="size-4 shrink-0 text-zinc-400" />
        </button>
      </PO.Trigger>
      <PO.Portal>
        <PO.Content
          sideOffset={6}
          align="start"
          className="z-50 w-[var(--radix-popover-trigger-width)] min-w-64 overflow-hidden rounded-lg border border-zinc-200/80 bg-popover shadow-md data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.97] duration-150"
        >
          <div className="flex items-center gap-2 border-b border-zinc-100 px-3">
            <Search className="size-4 shrink-0 text-zinc-400" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={searchPlaceholder}
              className="h-10 w-full bg-transparent text-sm outline-none placeholder:text-zinc-400"
            />
          </div>
          <div ref={listRef} className="max-h-64 overflow-y-auto p-1" role="listbox">
            {filtered.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-zinc-500">{emptyText}</p>
            ) : (
              filtered.map((o, i) => (
                <div
                  key={o.value}
                  role="option"
                  aria-selected={o.value === value}
                  data-index={i}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => pick(o)}
                  className={cn(
                    'relative flex cursor-pointer select-none items-start rounded-md py-2 pl-8 pr-3 text-sm text-zinc-700',
                    i === active && 'bg-zinc-100 text-zinc-900',
                  )}
                >
                  {o.value === value && <Check className="absolute left-2.5 top-2.5 size-4 text-brand-600" />}
                  <span className="min-w-0 flex-1 break-words">{o.label}</span>
                </div>
              ))
            )}
          </div>
        </PO.Content>
      </PO.Portal>
    </PO.Root>
  )
}
