import { MoreHorizontal, Pencil, Plus, Power, UserPlus } from 'lucide-react'
import { formatRelative } from '@/shared/lib/format'
import { Avatar } from '@/shared/ui/avatar'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { type Column, DataList } from '@/shared/ui/data-list'
import { EmptyState, ErrorState, NoResults } from '@/shared/ui/feedback'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/shared/ui/menus'
import { ConfirmDialog } from '@/shared/ui/misc'
import { PageContainer, PageHeader, Pagination, SearchInput, Segmented } from '@/shared/ui/page'
import type { User } from '../api/users-service'
import { UserFormSheet } from '../components/UserFormSheet'
import { useUsersViewModel } from '../hooks/use-users-view-model'

function StatusBadge({ user }: { user: User }) {
  if (!user.is_active) return <Badge tone="neutral" dot>Inactivo</Badge>
  if (user.must_change_password) return <Badge tone="warning" dot>Pendiente de ingreso</Badge>
  return <Badge tone="success" dot>Activo</Badge>
}

export default function UsersPage() {
  const vm = useUsersViewModel()
  const data = vm.query.data

  const actions = (u: User) =>
    vm.canManage && (
      <DropdownMenu>
        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
          <Button variant="ghost" size="icon-sm" aria-label={`Acciones para ${u.full_name}`}>
            <MoreHorizontal />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
          <DropdownMenuItem onSelect={() => vm.openEdit(u)}>
            <Pencil /> Editar
          </DropdownMenuItem>
          <DropdownMenuItem destructive={u.is_active} onSelect={() => vm.askToggle(u)}>
            <Power /> {u.is_active ? 'Desactivar' : 'Reactivar'}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )

  const columns: Column<User>[] = [
    {
      key: 'name',
      header: 'Usuario',
      cell: (u) => (
        <div className="flex items-center gap-3">
          <Avatar name={u.full_name} />
          <div className="min-w-0">
            <p className="truncate font-medium text-zinc-900">{u.full_name}</p>
            <p className="truncate text-xs text-muted-foreground">{u.email}</p>
          </div>
        </div>
      ),
    },
    { key: 'roles', header: 'Rol', cell: (u) => <div className="flex flex-wrap gap-1">{u.roles.map((r) => <Badge key={r.id} tone={r.code === 'ADMIN' ? 'dark' : r.code === 'MANAGER' ? 'brand' : 'neutral'}>{r.name}</Badge>)}</div> },
    { key: 'status', header: 'Estado', cell: (u) => <StatusBadge user={u} /> },
    { key: 'last', header: 'Último ingreso', cell: (u) => <span className="text-zinc-600">{formatRelative(u.last_login_at)}</span> },
    { key: 'actions', header: <span className="sr-only">Acciones</span>, className: 'w-12 text-right', cell: actions },
  ]

  const filtered = !!vm.search || vm.status !== 'active'

  return (
    <PageContainer>
      <PageHeader
        title="Usuarios"
        description="Personas con acceso al CRM y su rol."
        actions={vm.canManage && (
          <Button onClick={vm.openCreate}>
            <Plus /> Nuevo usuario
          </Button>
        )}
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-zinc-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <SearchInput value={vm.search} onChange={vm.setSearch} placeholder="Buscar por nombre o correo" className="sm:max-w-xs sm:flex-1" />
          <Segmented
            value={vm.status}
            onChange={vm.setStatus}
            options={[
              { value: 'active', label: 'Activos' },
              { value: 'inactive', label: 'Inactivos' },
              { value: 'all', label: 'Todos' },
            ]}
          />
        </div>

        {vm.query.isError ? (
          <ErrorState error={vm.query.error} onRetry={() => vm.query.refetch()} />
        ) : (
          <DataList
            items={data?.items}
            loading={vm.query.isPending}
            columns={columns}
            getKey={(u) => u.id}
            onItemClick={vm.canManage ? vm.openEdit : undefined}
            renderCard={(u) => (
              <div className="flex items-center gap-3">
                <Avatar name={u.full_name} className="size-10" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-zinc-900">{u.full_name}</p>
                  <p className="truncate text-xs text-muted-foreground">{u.roles.map((r) => r.name).join(', ')} · {u.email}</p>
                  <div className="mt-1.5"><StatusBadge user={u} /></div>
                </div>
                {actions(u)}
              </div>
            )}
            empty={
              filtered ? (
                <NoResults onClear={vm.clearFilters} />
              ) : (
                <EmptyState
                  icon={<UserPlus />}
                  title="Aún no hay usuarios"
                  description="Crea los usuarios del equipo comercial para empezar."
                  action={vm.canManage && <Button onClick={vm.openCreate}><Plus /> Nuevo usuario</Button>}
                />
              )
            }
            footer={data && <Pagination page={vm.page} pageSize={data.page_size} total={data.total} onPageChange={vm.setPage} />}
          />
        )}
      </Card>

      <UserFormSheet user={vm.editing} onClose={vm.closeEditor} onSaved={vm.onSaved} />
      <ConfirmDialog
        open={!!vm.confirming}
        onOpenChange={(o) => !o && vm.closeConfirm()}
        title={`¿Desactivar a ${vm.confirming?.full_name}?`}
        description="No podrá ingresar al CRM y sus sesiones activas se cerrarán. Su historial se conserva y puedes reactivarlo cuando quieras."
        confirmLabel="Desactivar"
        destructive
        onConfirm={vm.confirmToggle}
      />
    </PageContainer>
  )
}
