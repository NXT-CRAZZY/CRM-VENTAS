import { Menu } from 'lucide-react'
import { Dialog as D } from 'radix-ui'
import { useState } from 'react'
import { NavLink } from 'react-router'
import { usePermissions } from '@/shared/auth/permissions'
import { cn } from '@/shared/lib/utils'
import { overlayClass } from '@/shared/ui/dialog'
import { Logo } from '@/shared/ui/misc'
import { NAV } from './nav-items'
import { NavSections } from './Sidebar'

/** Barra inferior para celular: accesos principales al alcance del pulgar + menú completo. */
export function MobileNav() {
  const { canAny } = usePermissions()
  const [open, setOpen] = useState(false)
  const items = NAV.flatMap((s) => s.items).filter(
    (i) => i.mobile && !i.soon && (!i.permission || canAny(...(Array.isArray(i.permission) ? i.permission : [i.permission]))),
  )

  const tab = 'flex flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors'

  return (
    <>
      <nav
        className="pb-safe fixed inset-x-0 bottom-0 z-40 border-t border-zinc-200/80 bg-white/90 backdrop-blur-md lg:hidden"
        aria-label="Navegación móvil"
      >
        <div className="flex h-16">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => cn(tab, isActive ? 'text-brand-700' : 'text-zinc-500 active:text-zinc-800')}
            >
              {({ isActive }) => (
                <>
                  <span className={cn('rounded-full px-4 py-1 transition-colors', isActive && 'bg-brand-50')}>
                    <Icon className="size-5" />
                  </span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
          <button type="button" onClick={() => setOpen(true)} className={cn(tab, 'text-zinc-500 active:text-zinc-800')}>
            <span className="px-4 py-1">
              <Menu className="size-5" />
            </span>
            Más
          </button>
        </div>
      </nav>

      <D.Root open={open} onOpenChange={setOpen}>
        <D.Portal>
          <D.Overlay className={overlayClass} />
          <D.Content className="fixed inset-y-0 left-0 z-50 flex w-[82vw] max-w-xs flex-col bg-ink-950 shadow-lg duration-250 data-[state=open]:animate-in data-[state=open]:slide-in-from-left data-[state=closed]:animate-out data-[state=closed]:slide-out-to-left">
            <D.Title className="sr-only">Menú</D.Title>
            <D.Description className="sr-only">Navegación del CRM</D.Description>
            <div className="flex h-16 items-center px-5">
              <Logo onDark className="h-7 w-auto" />
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-4">
              <NavSections onNavigate={() => setOpen(false)} />
            </div>
          </D.Content>
        </D.Portal>
      </D.Root>
    </>
  )
}
