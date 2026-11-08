import { cn, initials } from '@/shared/lib/utils'

// Tonos suaves para distinguir personas sin saturar la interfaz.
const TONES = [
  'bg-brand-100 text-brand-800',
  'bg-zinc-200 text-zinc-800',
  'bg-amber-100 text-amber-900',
  'bg-sky-100 text-sky-900',
  'bg-emerald-100 text-emerald-900',
]

export function Avatar({ name, className }: { name: string; className?: string }) {
  const tone = TONES[[...name].reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % TONES.length]
  return (
    <span
      className={cn(
        'inline-flex size-8 shrink-0 select-none items-center justify-center rounded-full text-xs font-semibold',
        tone,
        className,
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  )
}
