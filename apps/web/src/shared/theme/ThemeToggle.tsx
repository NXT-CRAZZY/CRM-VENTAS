import { Lightbulb } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useThemeStore } from './theme-store'

/** Interruptor tipo foquito: encendido = modo claro, apagado = modo oscuro. */
export function ThemeToggle({ className }: { className?: string }) {
  const dark = useThemeStore((s) => s.theme === 'dark')
  const toggle = useThemeStore((s) => s.toggle)
  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label="Modo oscuro"
      title={dark ? 'Encender (modo claro)' : 'Apagar (modo oscuro)'}
      onClick={toggle}
      className={cn(
        'relative inline-flex h-7 w-13 shrink-0 cursor-pointer items-center rounded-full p-0.5 ring-1 ring-inset transition-colors duration-300 focus-visible:ring-2 focus-visible:ring-ring/50',
        dark ? 'bg-zinc-200 ring-zinc-300' : 'bg-amber-100 ring-amber-200',
        className,
      )}
    >
      <span
        className={cn(
          'flex size-6 items-center justify-center rounded-full shadow-sm transition-all duration-300 ease-out',
          dark ? 'translate-x-6 bg-zinc-500 text-zinc-100' : 'translate-x-0 bg-amber-400 text-white shadow-[0_0_12px_2px_rgb(251_191_36/0.7)]',
        )}
      >
        <Lightbulb className={cn('size-3.5', !dark && 'fill-white')} />
      </span>
    </button>
  )
}
