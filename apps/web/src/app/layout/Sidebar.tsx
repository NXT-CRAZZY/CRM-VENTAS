import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { motion } from 'motion/react'
import { NavLink } from 'react-router'
import { usePermissions } from '@/shared/auth/permissions'
import { useUiStore } from '@/shared/stores/ui-store'
import { cn } from '@/shared/lib/utils'
import { Logo } from '@/shared/ui/misc'
import { Tooltip } from '@/shared/ui/menus'
import { type NavItem, visibleNav } from './nav-items'

export function NavEntry({ item, collapsed, onNavigate }: { item: NavItem; collapsed?: boolean; onNavigate?: () => void }) {
  const Icon = item.icon
  const base =
    'group relative flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors duration-150 lg:h-9'

  if (item.soon) {
    const content = (
      <div className={cn(base, 'cursor-default text-zinc-500/80')} aria-disabled>
        <Icon className="size-[18px] shrink-0 opacity-60" />
        {!collapsed && (
          <>
            <span className="truncate">{item.label}</span>
            <span className="ml-auto rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-zinc-500 ring-1 ring-inset ring-white/10">
              {item.soon}
            </span>
          </>
        )}
      </div>
    )
    return collapsed ? <Tooltip content={`${item.label} · ${item.soon}`} side="right">{content}</Tooltip> : content
  }

  const link = (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(base, isActive ? 'bg-white/[0.08] text-white' : 'text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-100')
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.span
              layoutId="nav-active"
              className="absolute inset-y-2 left-0 w-[3px] rounded-r-full bg-brand-600"
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            />
          )}
          <Icon className={cn('size-[18px] shrink-0', isActive ? 'text-brand-500' : 'text-zinc-500 group-hover:text-zinc-300')} />
          {!collapsed && <span className="truncate">{item.label}</span>}
        </>
      )}
    </NavLink>
  )
  return collapsed ? <Tooltip content={item.label} side="right">{link}</Tooltip> : link
}

export function NavSections({ collapsed, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const { can } = usePermissions()
  return (
    <nav className="space-y-6" aria-label="Navegación principal">
      {visibleNav(can).map((section, i) => (
        <div key={section.title ?? i}>
          {section.title &&
            (collapsed ? (
              <div className="mx-3 mb-2 h-px bg-white/[0.06]" />
            ) : (
              <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{section.title}</p>
            ))}
          <div className="space-y-0.5">
            {section.items.map((item) => (
              <NavEntry key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      ))}
    </nav>
  )
}

export function Sidebar() {
  const { sidebarCollapsed: collapsed, toggleSidebar } = useUiStore()
  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 hidden h-dvh shrink-0 flex-col bg-ink-950 lg:flex"
    >
      <div className={cn('flex h-16 items-center', collapsed ? 'justify-center' : 'px-5')}>
        <Logo onDark variant={collapsed ? 'mark' : 'full'} className={collapsed ? 'size-8' : 'h-7 w-auto'} />
      </div>
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        <NavSections collapsed={collapsed} />
      </div>
      <div className="border-t border-white/[0.06] p-3">
        <button
          type="button"
          onClick={toggleSidebar}
          className="flex h-9 w-full items-center gap-3 rounded-lg px-3 text-sm text-zinc-500 transition-colors hover:bg-white/[0.04] hover:text-zinc-200"
          aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'}
        >
          {collapsed ? <PanelLeftOpen className="size-[18px]" /> : <PanelLeftClose className="size-[18px]" />}
          {!collapsed && 'Contraer menú'}
        </button>
      </div>
    </motion.aside>
  )
}
