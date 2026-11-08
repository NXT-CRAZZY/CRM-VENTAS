import { Bell, Check, Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { P, usePermissions } from '@/shared/auth/permissions'
import { formatDateTime } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { DataList, type Column } from '@/shared/ui/data-list'
import { EmptyState, ErrorState } from '@/shared/ui/feedback'
import { PageContainer, PageHeader, Pagination, Segmented } from '@/shared/ui/page'

import { alertsService, type Alert, type AlertSeverity, type AlertStatus } from '../api/alerts-service'

const STATUS_OPTIONS: { value: AlertStatus | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'Todas' },
  { value: 'UNREAD', label: 'Sin leer' },
  { value: 'READ', label: 'Leídas' },
  { value: 'DISMISSED', label: 'Descartadas' },
]

const SEVERITY_OPTIONS: { value: AlertSeverity | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'Todas' },
  { value: 'CRITICAL', label: 'Crítica' },
  { value: 'HIGH', label: 'Alta' },
  { value: 'MEDIUM', label: 'Media' },
  { value: 'LOW', label: 'Baja' },
]

function severityTone(severity: AlertSeverity) {
  switch (severity) {
    case 'CRITICAL':
    case 'HIGH':
      return 'danger'
    case 'MEDIUM':
      return 'warning'
    case 'LOW':
      return 'neutral'
    default:
      return 'neutral'
  }
}

function alertTypeLabel(type: Alert['alert_type']) {
  const labels: Record<string, string> = {
    NO_FIRST_CONTACT: 'Sin primer contacto',
    NO_FOLLOWUP: 'Sin seguimiento',
    QUOTE_EXPIRING: 'Cotización por vencer',
    QUOTE_NO_RESPONSE: 'Cotización sin respuesta',
    STALLED: 'Prospecto estancado',
    HIGH_VALUE: 'Oportunidad de alto valor',
  }
  return labels[type] ?? type
}

export default function AlertsPage() {
  const { can } = usePermissions()
  const canGenerate = can(P.DASHBOARD_SALES)
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<AlertStatus | 'ALL'>('UNREAD')
  const [severity, setSeverity] = useState<AlertSeverity | 'ALL'>('ALL')
  const [page, setPage] = useState(1)

  const listQ = useQuery({
    queryKey: ['alerts', { status, severity, page }],
    queryFn: () =>
      alertsService.list({
        status: status === 'ALL' ? undefined : status,
        severity: severity === 'ALL' ? undefined : severity,
        page,
        page_size: 20,
      }),
  })

  const generateM = useMutation({
    mutationFn: () => alertsService.generate(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alerts', 'unread-count'] })
    },
  })

  const markReadM = useMutation({
    mutationFn: (id: string) => alertsService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alerts', 'unread-count'] })
    },
  })

  const dismissM = useMutation({
    mutationFn: (id: string) => alertsService.dismiss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alerts', 'unread-count'] })
    },
  })

  const alerts = listQ.data?.items ?? []

  const columns: Column<Alert>[] = [
    {
      key: 'severity',
      header: 'Severidad',
      className: 'w-28',
      cell: (a) => <Badge tone={severityTone(a.severity)}>{a.severity}</Badge>,
    },
    {
      key: 'type',
      header: 'Tipo',
      className: 'w-44',
      cell: (a) => <span className="text-sm text-zinc-700">{alertTypeLabel(a.alert_type)}</span>,
    },
    {
      key: 'title',
      header: 'Alerta',
      cell: (a) => (
        <div>
          <p className="font-medium text-zinc-900">{a.title}</p>
          <p className="text-sm text-zinc-500">{a.message}</p>
        </div>
      ),
    },
    {
      key: 'prospect',
      header: 'Prospecto',
      className: 'w-48',
      cell: (a) =>
        a.prospect_name ? (
          <span className="text-sm text-zinc-700">{a.prospect_name}</span>
        ) : (
          <span className="text-sm text-zinc-400">—</span>
        ),
    },
    {
      key: 'created',
      header: 'Fecha',
      className: 'w-40',
      cell: (a) => <span className="text-sm text-zinc-500">{formatDateTime(a.created_at)}</span>,
    },
    {
      key: 'actions',
      header: '',
      className: 'w-32 text-right',
      cell: (a) =>
        a.status !== 'DISMISSED' && (
          <div className="flex items-center justify-end gap-1">
            {a.status === 'UNREAD' && (
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label="Marcar como leída"
                onClick={(e) => {
                  e.stopPropagation()
                  markReadM.mutate(a.id)
                }}
              >
                <Check className="size-4" />
              </Button>
            )}
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label="Descartar"
              onClick={(e) => {
                e.stopPropagation()
                dismissM.mutate(a.id)
              }}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
        ),
    },
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Alertas"
        description="Alertas automáticas de seguimiento, cotizaciones y oportunidades."
        actions={
          canGenerate && (
            <Button
              variant="outline"
              onClick={() => generateM.mutate()}
              disabled={generateM.isPending}
            >
              {generateM.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : <RefreshCw className="mr-2 size-4" />}
              Generar ahora
            </Button>
          )
        }
      />

      <Card className="mb-6 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <Segmented
            value={status}
            onChange={(v) => {
              setStatus(v as AlertStatus | 'ALL')
              setPage(1)
            }}
            options={STATUS_OPTIONS}
          />
          <Segmented
            value={severity}
            onChange={(v) => {
              setSeverity(v as AlertSeverity | 'ALL')
              setPage(1)
            }}
            options={SEVERITY_OPTIONS}
          />
        </div>
      </Card>

      <Card>
        {listQ.isError ? (
          <ErrorState error={listQ.error} onRetry={() => listQ.refetch()} />
        ) : (
          <>
            <DataList
              items={alerts}
              columns={columns}
              getKey={(a) => a.id}
              loading={listQ.isLoading}
              empty={<EmptyState icon={<Bell />} title="Sin alertas" description="No hay alertas que coincidan con los filtros seleccionados." />}
              renderCard={(a) => (
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <Badge tone={severityTone(a.severity)}>{a.severity}</Badge>
                    <span className="text-xs text-zinc-400">{formatDateTime(a.created_at)}</span>
                  </div>
                  <p className="font-medium text-zinc-900">{a.title}</p>
                  <p className="text-sm text-zinc-500">{a.message}</p>
                </div>
              )}
            />
            {!!listQ.data && listQ.data.total > 0 && (
              <Pagination
                page={page}
                pageSize={20}
                total={listQ.data.total}
                onPageChange={setPage}
              />
            )}
          </>
        )}
      </Card>
    </PageContainer>
  )
}
