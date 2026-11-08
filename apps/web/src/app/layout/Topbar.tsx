import { KeyRound, LogOut } from 'lucide-react'
import { useState } from 'react'
import { authService } from '@/features/auth/api/auth-service'
import { ChangePasswordForm } from '@/features/auth/components/ChangePasswordForm'
import { useSessionStore } from '@/shared/auth/session-store'
import { Avatar } from '@/shared/ui/avatar'
import { Dialog, DialogContent, DialogHeader } from '@/shared/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/menus'
import { Logo } from '@/shared/ui/misc'

export function UserMenu() {
  const user = useSessionStore((s) => s.user)
  const [pwdOpen, setPwdOpen] = useState(false)
  if (!user) return null
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2.5 rounded-full p-0.5 pr-1 transition-colors hover:bg-zinc-100 focus-visible:ring-2 focus-visible:ring-ring/40 sm:rounded-lg sm:pr-2"
          >
            <Avatar name={user.full_name} />
            <span className="hidden text-left sm:block">
              <span className="block max-w-40 truncate text-[13px] font-medium leading-tight text-zinc-900">{user.full_name}</span>
              <span className="block text-xs leading-tight text-zinc-500">{user.roles.map((r) => r.name).join(', ')}</span>
            </span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          <DropdownMenuLabel className="font-normal">
            <span className="block truncate text-sm font-medium text-zinc-900">{user.full_name}</span>
            <span className="block truncate">{user.email}</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setPwdOpen(true)}>
            <KeyRound /> Cambiar contraseña
          </DropdownMenuItem>
          <DropdownMenuItem destructive onSelect={() => authService.logout()}>
            <LogOut /> Cerrar sesión
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Dialog open={pwdOpen} onOpenChange={setPwdOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader title="Cambiar contraseña" description="Usa al menos 8 caracteres, con letras y números." />
          <ChangePasswordForm onDone={() => setPwdOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  )
}

export function Topbar() {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-zinc-200/70 bg-white/80 px-4 backdrop-blur-md supports-[backdrop-filter]:bg-white/70 sm:px-6 lg:h-16 lg:px-8">
      <Logo variant="mark" className="size-7 lg:hidden" />
      <span className="text-sm font-semibold text-zinc-900 lg:hidden">CRM</span>
      <div className="ml-auto flex items-center gap-2">
        <UserMenu />
      </div>
    </header>
  )
}
