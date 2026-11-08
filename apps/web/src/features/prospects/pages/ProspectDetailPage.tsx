import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Mail, MapPin, Phone, UsersRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { type Schemas } from '@/shared/api/client'
import { errorMessage } from '@/shared/api/errors'
import { P, usePermissions } from '@/shared/auth/permissions'
import { formatDate, formatDateTime, formatPhone } from '@/shared/lib/format'
import { Avatar } from '@/shared/ui/avatar'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { ErrorState } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { PageContainer, PageHeader, Segmented } from '@/shared/ui/page'

import { InteractionsSection } from '@/features/interactions/components/InteractionsSection'
import { OpportunitiesSection } from '@/features/opportunities/components/OpportunitiesSection'
import { QuotesSection } from '@/features/quotes/components/QuotesSection'
import { TasksSection } from '@/features/tasks/components/TasksSection'

import { prospectsKeys, prospectsService } from '../api/prospects-service'
import { ProspectActionsMenu } from '../components/ProspectActionsMenu'
import { ProspectAssignDialog } from '../components/ProspectAssignDialog'
import { ProspectFormSheet } from '../components/ProspectFormSheet'
import { ProspectStatusDialog } from '../components/ProspectStatusDialog'

type ActionState =
  | { type: 'assign' }
  | { type: 'status' }
  | { type: 'delete' }
  | null

export default function ProspectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { can } = usePermissions()
  const canUpdate = can(P.PROSPECTS_UPDATE_OWN) || can(P.PROSPECTS_UPDATE_ALL)
  const canAssign = can(P.PROSPECTS_ASSIGN)
  const canDelete = can(P.PROSPECTS_DELETE)

  const [tab, setTab] = useState<'resumen' | 'contactos' | 'interacciones' | 'tareas' | 'oportunidades' | 'cotizaciones' | 'historial'>('resumen')
  const [editing, setEditing] = useState(false)
  const [action, setAction] = useState<ActionState>(null)

  const prospectQ = useQuery({
    queryKey: prospectsKeys.detail(id!),
    queryFn: () => prospectsService.get(id!),
    enabled: !!id,
  })
  const assignmentsQ = useQuery({
    queryKey: [...prospectsKeys.detail(id!), 'assignments'],
    queryFn: () => prospectsService.getAssignments(id!),
    enabled: !!id && tab === 'historial',
  })
  const historyQ = useQuery({
    queryKey: [...prospectsKeys.detail(id!), 'status-history'],
    queryFn: () => prospectsService.getStatusHistory(id!),
    enabled: !!id && tab === 'historial',
  })

  const assignMutation = useMutation({
    mutationFn: ({ targetId, ...body }: { targetId: string } & Schemas['AssignRequest']) =>
      prospectsService.assign(targetId, body),
    onSuccess: () => {
      toast.success('Prospecto asignado')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.detail(id!) })
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const statusMutation = useMutation({
    mutationFn: ({ targetId, ...body }: { targetId: string } & Schemas['StatusChangeRequest']) =>
      prospectsService.changeStatus(targetId, body),
    onSuccess: () => {
      toast.success('Estado actualizado')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.detail(id!) })
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: prospectsService.delete,
    onSuccess: () => {
      toast.success('Prospecto eliminado')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
      navigate('/prospectos')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const prospect = prospectQ.data
  if (prospectQ.error) {
    return (
      <PageContainer>
        <ErrorState error={prospectQ.error} />
      </PageContainer>
    )
  }
  if (!prospect) {
    return (
      <PageContainer>
        <div className="py-12 text-center text-muted-foreground">Cargando ficha…</div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <div className="mb-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/prospectos">
            <ArrowLeft /> Volver al listado
          </Link>
        </Button>
      </div>

      <PageHeader
        title={
          <div className="flex items-center gap-3">
            <Avatar name={prospect.display_name} />
            <div>
              <h1 className="text-xl font-semibold">{prospect.display_name}</h1>
              <p className="text-sm text-muted-foreground">{prospect.code}</p>
            </div>
          </div>
        }
        description={
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone={prospect.person_type === 'NATURAL' ? 'neutral' : 'brand'}>
              {prospect.person_type === 'NATURAL' ? 'Natural' : 'Jurídica'}
            </Badge>
            <Badge tone={prospect.relationship_type === 'CLIENTE' ? 'success' : 'neutral'}>
              {prospect.relationship_type === 'CLIENTE' ? 'Cliente' : 'Prospecto'}
            </Badge>
            <Badge tone="neutral">{prospect.status}</Badge>
          </div>
        }
        actions={
          (canUpdate || canAssign || canDelete) && (
            <ProspectActionsMenu
              prospect={prospect}
              label="Acciones de la ficha"
              onEdit={canUpdate ? () => setEditing(true) : undefined}
              onAssign={canAssign ? () => setAction({ type: 'assign' }) : undefined}
              onChangeStatus={canUpdate ? () => setAction({ type: 'status' }) : undefined}
              onDelete={canDelete ? () => setAction({ type: 'delete' }) : undefined}
            />
          )
        }
      />

      <Segmented
        value={tab}
        onChange={(v) => setTab(v as typeof tab)}
        options={[
          { value: 'resumen', label: 'Resumen' },
          { value: 'contactos', label: `Contactos (${prospect.contacts.length})` },
          { value: 'interacciones', label: `Interacciones (${prospect.interaction_count})` },
          { value: 'tareas', label: 'Tareas' },
          { value: 'oportunidades', label: 'Oportunidades' },
          { value: 'cotizaciones', label: 'Cotizaciones' },
          { value: 'historial', label: 'Historial' },
        ]}
        className="mb-6"
      />

      {tab === 'resumen' && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="space-y-4 p-5 lg:col-span-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Información de contacto</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {prospect.email && (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="size-4 text-zinc-400" />
                  <a href={`mailto:${prospect.email}`} className="text-brand-700 hover:underline">
                    {prospect.email}
                  </a>
                </div>
              )}
              {prospect.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="size-4 text-zinc-400" />
                  <a href={`tel:${prospect.phone}`} className="text-brand-700 hover:underline">
                    {formatPhone(prospect.phone)}
                  </a>
                </div>
              )}
              {prospect.whatsapp && (
                <div className="flex items-center gap-2 text-sm">
                  <UsersRound className="size-4 text-zinc-400" />
                  <a
                    href={`https://wa.me/${prospect.whatsapp.replace(/\D/g, '')}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-700 hover:underline"
                  >
                    {formatPhone(prospect.whatsapp)}
                  </a>
                </div>
              )}
              {prospect.address && (
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="size-4 text-zinc-400" />
                  <span>{prospect.address}</span>
                </div>
              )}
            </div>
            {prospect.notes && (
              <>
                <hr className="border-zinc-100" />
                <div>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Notas</h2>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700">{prospect.notes}</p>
                </div>
              </>
            )}
          </Card>

          <Card className="space-y-4 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Resumen comercial</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Responsable</span>
                <span className="font-medium">{prospect.owner.full_name}</span>
              </div>
              {prospect.interest_level && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Interés</span>
                  <span className="font-medium">{prospect.interest_level.name}</span>
                </div>
              )}
              {prospect.priority && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Prioridad</span>
                  <span className="font-medium">{prospect.priority.name}</span>
                </div>
              )}
              {prospect.source && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Origen</span>
                  <span className="font-medium">{prospect.source.name}</span>
                </div>
              )}
              {prospect.birth_date && prospect.person_type === 'NATURAL' && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Fecha de nacimiento</span>
                  <span className="font-medium">{formatDate(prospect.birth_date)}</span>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {tab === 'contactos' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {prospect.contacts.length === 0 && (
            <Card className="p-5 text-sm text-muted-foreground">No hay contactos registrados.</Card>
          )}
          {prospect.contacts.map((c) => (
            <Card key={c.id} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-zinc-900">{c.full_name}</p>
                  {(c.position || c.area) && (
                    <p className="text-xs text-muted-foreground">
                      {[c.position, c.area].filter(Boolean).join(' · ')}
                    </p>
                  )}
                </div>
                {c.is_primary && <Badge tone="brand">Principal</Badge>}
              </div>
              <div className="mt-3 space-y-1 text-sm">
                {c.email && <p className="text-zinc-700">{c.email}</p>}
                {c.phone && <p className="text-muted-foreground">{formatPhone(c.phone)}</p>}
                {c.whatsapp && <p className="text-muted-foreground">WhatsApp: {formatPhone(c.whatsapp)}</p>}
              </div>
              {c.notes && <p className="mt-3 text-xs text-zinc-600">{c.notes}</p>}
            </Card>
          ))}
        </div>
      )}

      {tab === 'interacciones' && id && (
        <InteractionsSection prospectId={id} contacts={prospect.contacts} canUpdate={canUpdate} />
      )}

      {tab === 'tareas' && id && <TasksSection prospectId={id} />}

      {tab === 'oportunidades' && id && <OpportunitiesSection prospectId={id} />}

      {tab === 'cotizaciones' && id && <QuotesSection prospectId={id} />}

      {tab === 'historial' && (
        <Card className="p-0">
          <div className="divide-y divide-zinc-100">
            {assignmentsQ.isLoading || historyQ.isLoading ? (
              <p className="p-5 text-sm text-muted-foreground">Cargando historial…</p>
            ) : (
              [
                ...(assignmentsQ.data ?? []).map((a) => ({
                  key: `a-${a.id}`,
                  date: a.assigned_at,
                  text: (
                    <>
                      Asignado a <strong>{a.to_user.full_name}</strong>
                      {a.from_user && <> desde {a.from_user.full_name}</>}
                      {a.reason && <> · {a.reason}</>}
                    </>
                  ),
                })),
                ...(historyQ.data ?? []).map((h) => ({
                  key: `h-${h.id}`,
                  date: h.created_at,
                  text: (
                    <>
                      Estado cambiado de <strong>{h.from_status ?? '—'}</strong> a{' '}
                      <strong>{h.to_status}</strong>
                      {h.reason && <> · {h.reason}</>}
                      {h.changed_by && <> por {h.changed_by.full_name}</>}
                    </>
                  ),
                })),
              ]
                .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                .map((e) => (
                  <div key={e.key} className="flex items-start gap-3 p-4 text-sm">
                    <div className="mt-0.5 size-2 rounded-full bg-brand-500" />
                    <div className="flex-1">
                      <p className="text-zinc-800">{e.text}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{formatDateTime(e.date)}</p>
                    </div>
                  </div>
                ))
            )}
            {(assignmentsQ.data?.length === 0 && historyQ.data?.length === 0) && (
              <p className="p-5 text-sm text-muted-foreground">Sin historial aún.</p>
            )}
          </div>
        </Card>
      )}

      {canUpdate && (
        <ProspectFormSheet prospect={editing ? prospect : null} onClose={() => setEditing(false)} />
      )}

      <ProspectAssignDialog
        open={action?.type === 'assign'}
        onOpenChange={(open) => !open && setAction(null)}
        title="Asignar prospecto"
        description={`Selecciona el nuevo responsable de ${prospect.display_name}.`}
        pending={assignMutation.isPending}
        onAssign={(values) => {
          if (!id) return
          assignMutation.mutate({ targetId: id, owner_id: values.owner_id, reason: values.reason ?? undefined })
          setAction(null)
        }}
      />

      <ProspectStatusDialog
        open={action?.type === 'status'}
        onOpenChange={(open) => !open && setAction(null)}
        currentStatus={prospect.status}
        pending={statusMutation.isPending}
        onChange={(values) => {
          if (!id) return
          statusMutation.mutate({ targetId: id, status: values.status, reason: values.reason })
          setAction(null)
        }}
      />

      <ConfirmDialog
        open={action?.type === 'delete'}
        onOpenChange={(open) => !open && setAction(null)}
        title="¿Eliminar prospecto?"
        description={`Se eliminará "${prospect.display_name}". Esta acción se puede deshacer restaurándolo desde administración.`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={() => {
          if (!id) return
          deleteMutation.mutate(id)
          setAction(null)
        }}
      />
    </PageContainer>
  )
}
