import { Clock, Flame, Phone, UserPlus, UsersRound, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { P, usePermissions } from '@/shared/auth/permissions'
import { formatPhone } from '@/shared/lib/format'
import { Avatar } from '@/shared/ui/avatar'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { type Column, DataList } from '@/shared/ui/data-list'
import { EmptyState, NoResults } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { Checkbox } from '@/shared/ui/menus'
import { PageContainer, PageHeader, Pagination, SearchInput, Segmented } from '@/shared/ui/page'

import { type Prospect } from '../api/prospects-service'
import { ProspectActionsMenu } from '../components/ProspectActionsMenu'
import { ProspectAssignDialog } from '../components/ProspectAssignDialog'
import { ProspectFormSheet } from '../components/ProspectFormSheet'
import { ProspectStatusDialog } from '../components/ProspectStatusDialog'
import { useProspectsViewModel } from '../hooks/use-prospects-view-model'
import { STATUS_OPTIONS } from '../model/constants'

function PersonTypeBadge({ type }: { type: Prospect['person_type'] }) {
  if (type === 'NATURAL') return <Badge tone="neutral">Natural</Badge>
  return <Badge tone="brand">Jurídica</Badge>
}

function RelationshipBadge({ type }: { type: Prospect['relationship_type'] }) {
  if (type === 'CLIENTE') return <Badge tone="success">Cliente</Badge>
  return <Badge tone="neutral">Prospecto</Badge>
}

type ActionState =
  | { type: 'assign'; prospect: Prospect }
  | { type: 'status'; prospect: Prospect }
  | { type: 'delete'; prospect: Prospect }
  | null

function QuickFilterChip({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ElementType
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors
        ${active ? 'bg-brand-50 text-brand-700 ring-brand-200' : 'bg-card text-zinc-600 ring-zinc-200 hover:bg-zinc-50 hover:text-zinc-900'}
      `}
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  )
}

function hasAdvancedFilters(filters: ReturnType<typeof useProspectsViewModel>['filters']) {
  return (
    filters.without_contact_days != null ||
    filters.next_action_today === true ||
    filters.created_since_days != null ||
    filters.interest_level_code != null ||
    filters.relationship_type != null ||
    filters.person_type != null ||
    filters.owner_id != null ||
    filters.priority_id != null ||
    filters.source_id != null
  )
}

export default function ProspectsPage() {
  const { can } = usePermissions()
  const canCreate = can(P.PROSPECTS_CREATE)
  const canUpdate = can(P.PROSPECTS_UPDATE_OWN) || can(P.PROSPECTS_UPDATE_ALL)
  const canAssign = can(P.PROSPECTS_ASSIGN)
  const canDelete = can(P.PROSPECTS_DELETE)

  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [editing, setEditing] = useState<Prospect | 'new' | null>(searchParams.get('action') === 'new' ? 'new' : null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [bulkAssignOpen, setBulkAssignOpen] = useState(false)
  const [action, setAction] = useState<ActionState>(null)

  useEffect(() => {
    if (editing !== 'new' && searchParams.get('action') === 'new') {
      setEditing('new')
    }
  }, [searchParams, editing])

  const handleCloseForm = () => {
    setEditing(null)
    if (searchParams.get('action') === 'new') {
      const next = new URLSearchParams(searchParams)
      next.delete('action')
      setSearchParams(next)
    }
  }

  const vm = useProspectsViewModel()
  const visibleIds = useMemo(() => vm.prospects.map((p) => p.id), [vm.prospects])

  // Clear selection when the visible page changes to avoid operating on hidden rows.
  useEffect(() => {
    setSelectedIds((prev) => prev.filter((id) => visibleIds.includes(id)))
  }, [visibleIds])

  const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id))

  const toggleRow = (id: string, checked: boolean) => {
    setSelectedIds((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)))
  }

  const toggleAll = () => {
    setSelectedIds((prev) => {
      if (allSelected) return prev.filter((id) => !visibleIds.includes(id))
      return Array.from(new Set([...prev, ...visibleIds]))
    })
  }

  const handleAssign = (values: { owner_id: string; reason: string | null }) => {
    if (!action || action.type !== 'assign') return
    vm.assign({ id: action.prospect.id, owner_id: values.owner_id, reason: values.reason ?? undefined })
    setAction(null)
  }

  const handleChangeStatus = (values: { status: Prospect['status']; reason: string }) => {
    if (!action || action.type !== 'status') return
    vm.changeStatus({ id: action.prospect.id, status: values.status, reason: values.reason })
    setAction(null)
  }

  const handleDelete = async () => {
    if (!action || action.type !== 'delete') return
    vm.deleteProspect(action.prospect.id)
    setAction(null)
  }

  const handleBulkAssign = (values: { owner_id: string; reason: string | null }) => {
    if (selectedIds.length === 0) return
    vm.bulkAssign({ prospect_ids: selectedIds, owner_id: values.owner_id, reason: values.reason ?? undefined })
    setBulkAssignOpen(false)
    setSelectedIds([])
  }

  const columns: Column<Prospect>[] = [
    {
      key: 'select',
      header: (
        <span className="flex justify-center" onClick={(e) => e.stopPropagation()}>
          <Checkbox checked={allSelected} onCheckedChange={toggleAll} aria-label="Seleccionar todos" />
        </span>
      ),
      className: 'w-12 text-center',
      cell: (p) => (
        <span
          className="flex justify-center"
          onClick={(e) => {
            e.stopPropagation()
            e.preventDefault()
          }}
        >
          <Checkbox
            checked={selectedIds.includes(p.id)}
            onCheckedChange={(v) => toggleRow(p.id, !!v)}
            aria-label={`Seleccionar ${p.display_name}`}
          />
        </span>
      ),
    },
    {
      key: 'name',
      header: 'Prospecto',
      cell: (p) => (
        <div className="flex items-center gap-3">
          <Avatar name={p.display_name} className="size-7 text-[11px]" />
          <div className="min-w-0">
            <p className="font-medium text-zinc-900">{p.display_name}</p>
            <p className="text-xs text-muted-foreground">{p.code}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Tipo',
      cell: (p) => (
        <div className="flex flex-wrap gap-1">
          <PersonTypeBadge type={p.person_type} />
          <RelationshipBadge type={p.relationship_type} />
        </div>
      ),
    },
    {
      key: 'contact',
      header: 'Contacto',
      cell: (p) => (
        <div className="text-sm">
          {p.email && <p className="text-zinc-700">{p.email}</p>}
          {p.phone && <p className="text-muted-foreground">{formatPhone(p.phone)}</p>}
        </div>
      ),
    },
    {
      key: 'owner',
      header: 'Responsable',
      cell: (p) => <p className="text-sm text-zinc-700">{p.owner.full_name}</p>,
    },
    {
      key: 'actions',
      header: <span className="sr-only">Acciones</span>,
      className: 'w-12 text-right',
      cell: (p) => (
        <ProspectActionsMenu
          prospect={p}
          onEdit={canUpdate ? () => setEditing(p) : undefined}
          onAssign={canAssign ? () => setAction({ type: 'assign', prospect: p }) : undefined}
          onChangeStatus={canUpdate ? () => setAction({ type: 'status', prospect: p }) : undefined}
          onDelete={canDelete ? () => setAction({ type: 'delete', prospect: p }) : undefined}
        />
      ),
    },
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Prospectos"
        description="Gestión de personas naturales y jurídicas: cada prospecto tiene tipo, estado, responsable y próxima acción."
        actions={
          canCreate && (
            <Button onClick={() => setEditing('new')}>
              <UsersRound /> Nuevo prospecto
            </Button>
          )
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-zinc-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <SearchInput
            value={vm.search}
            onChange={(v) => vm.setSearch(v)}
            placeholder="Buscar por nombre, correo, teléfono, documento o código"
            className="sm:max-w-md sm:flex-1"
          />
          <Segmented
            value={vm.filters.status ?? 'ACTIVO'}
            onChange={(v) => vm.setFilters((f) => ({ ...f, status: v as Prospect['status'], page: 1 }))}
            options={STATUS_OPTIONS}
          />
        </div>

        <div className="flex flex-wrap gap-2 border-b border-zinc-100 bg-zinc-50/50 px-4 py-3">
          <QuickFilterChip
            active={vm.filters.without_contact_days === 7}
            onClick={() => vm.setFilters((f) => ({ ...f, without_contact_days: f.without_contact_days === 7 ? undefined : 7, page: 1 }))}
            icon={Clock}
            label="Sin contacto > 7 días"
          />
          <QuickFilterChip
            active={vm.filters.next_action_today === true}
            onClick={() => vm.setFilters((f) => ({ ...f, next_action_today: f.next_action_today ? undefined : true, page: 1 }))}
            icon={Phone}
            label="Seguimientos hoy"
          />
          <QuickFilterChip
            active={vm.filters.created_since_days === 7}
            onClick={() => vm.setFilters((f) => ({ ...f, created_since_days: f.created_since_days === 7 ? undefined : 7, page: 1 }))}
            icon={UserPlus}
            label="Nuevos últimos 7 días"
          />
          <QuickFilterChip
            active={vm.filters.interest_level_code === 'ALTO'}
            onClick={() => vm.setFilters((f) => ({ ...f, interest_level_code: f.interest_level_code === 'ALTO' ? undefined : 'ALTO', page: 1 }))}
            icon={Flame}
            label="Alto interés"
          />
          {hasAdvancedFilters(vm.filters) && (
            <button
              onClick={() => {
                vm.setSearch('')
                vm.setFilters({ page: 1, status: vm.filters.status })
              }}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
            >
              <X className="size-3.5" /> Limpiar filtros
            </button>
          )}
        </div>

        {selectedIds.length > 0 && (
          <div className="flex items-center justify-between gap-3 border-b border-zinc-100 bg-zinc-50/70 px-4 py-2.5">
            <span className="text-sm text-zinc-700">
              <strong>{selectedIds.length}</strong> prospecto(s) seleccionado(s)
            </span>
            <div className="flex items-center gap-2">
              {canAssign && (
                <Button size="sm" onClick={() => setBulkAssignOpen(true)}>
                  Asignar a…
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>
                Limpiar
              </Button>
            </div>
          </div>
        )}

        <DataList
          items={vm.prospects}
          loading={vm.isLoading}
          columns={columns}
          getKey={(p) => p.id}
          onItemClick={(p) => navigate(`/prospectos/${p.id}`)}
          renderCard={(p) => (
            <div className="flex items-start gap-3">
              <span
                className="mt-0.5"
                onClick={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                }}
              >
                <Checkbox
                  checked={selectedIds.includes(p.id)}
                  onCheckedChange={(v) => toggleRow(p.id, !!v)}
                  aria-label={`Seleccionar ${p.display_name}`}
                />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-zinc-900">{p.display_name}</p>
                <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  <span>{p.code}</span>·<span>{p.person_type === 'NATURAL' ? 'Natural' : 'Jurídica'}</span>
                  {p.phone && <>·<span>{formatPhone(p.phone)}</span></>}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  <RelationshipBadge type={p.relationship_type} />
                  <PersonTypeBadge type={p.person_type} />
                </div>
              </div>
              <ProspectActionsMenu
                prospect={p}
                onEdit={canUpdate ? () => setEditing(p) : undefined}
                onAssign={canAssign ? () => setAction({ type: 'assign', prospect: p }) : undefined}
                onChangeStatus={canUpdate ? () => setAction({ type: 'status', prospect: p }) : undefined}
                onDelete={canDelete ? () => setAction({ type: 'delete', prospect: p }) : undefined}
              />
            </div>
          )}
          empty={
            vm.search || vm.filters.status !== 'ACTIVO' || hasAdvancedFilters(vm.filters) ? (
              <NoResults onClear={() => { vm.setSearch(''); vm.setFilters({ page: 1, status: 'ACTIVO' }) }} />
            ) : (
              <EmptyState icon={<UsersRound />} title="Sin prospectos" />
            )
          }
          footer={<Pagination page={vm.page} pageSize={vm.pageSize} total={vm.total} onPageChange={(page) => vm.setFilters((f) => ({ ...f, page }))} />}
        />
      </Card>

      {(canCreate || canUpdate) && <ProspectFormSheet prospect={editing} onClose={handleCloseForm} />}

      <ProspectAssignDialog
        open={action?.type === 'assign'}
        onOpenChange={(open) => !open && setAction(null)}
        title="Asignar prospecto"
        description={`Selecciona el nuevo responsable de ${action?.type === 'assign' ? action.prospect.display_name : ''}.`}
        pending={vm.assignPending}
        onAssign={handleAssign}
      />

      <ProspectStatusDialog
        open={action?.type === 'status'}
        onOpenChange={(open) => !open && setAction(null)}
        currentStatus={action?.type === 'status' ? action.prospect.status : undefined}
        pending={vm.changeStatusPending}
        onChange={handleChangeStatus}
      />

      <ConfirmDialog
        open={action?.type === 'delete'}
        onOpenChange={(open) => !open && setAction(null)}
        title="¿Eliminar prospecto?"
        description={
          action?.type === 'delete'
            ? `Se eliminará "${action.prospect.display_name}". Esta acción se puede deshacer restaurándolo desde administración.`
            : ''
        }
        confirmLabel="Eliminar"
        destructive
        onConfirm={handleDelete}
      />

      <ProspectAssignDialog
        open={bulkAssignOpen}
        onOpenChange={setBulkAssignOpen}
        title={`Asignar ${selectedIds.length} prospecto(s)`}
        description="Selecciona el responsable que recibirá los prospectos seleccionados."
        confirmLabel="Asignar"
        pending={vm.bulkAssignPending}
        onAssign={handleBulkAssign}
      />
    </PageContainer>
  )
}
