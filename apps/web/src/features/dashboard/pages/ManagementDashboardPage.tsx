import {
  BarChart3,
  DollarSign,
  Filter,
  Loader2,
  RefreshCw,
  Trophy,
  TrendingUp,
  Users,
} from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { P, usePermissions } from '@/shared/auth/permissions'
import { formatDateTime, formatMoney } from '@/shared/lib/format'
import { fadeUp, stagger } from '@/shared/lib/motion'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'
import { EmptyState } from '@/shared/ui/feedback'
import { PageContainer, PageHeader } from '@/shared/ui/page'

import { dashboardService, type ManagementDashboard } from '../api/dashboard-service'

function KpiCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = 'neutral',
}: {
  label: string
  value: React.ReactNode
  hint?: string
  icon: React.ElementType
  tone?: 'neutral' | 'brand' | 'warning' | 'danger' | 'success'
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-4 p-5">
        <span
          className={{
            neutral: 'bg-zinc-50 text-zinc-500 ring-zinc-200',
            brand: 'bg-brand-50 text-brand-600 ring-brand-100',
            warning: 'bg-amber-50 text-amber-600 ring-amber-100',
            danger: 'bg-red-50 text-red-600 ring-red-100',
            success: 'bg-green-50 text-green-600 ring-green-100',
          }[tone] + ' rounded-lg p-2.5 ring-1 ring-inset'}
        >
          <Icon className="size-5" />
        </span>
        <div className="flex-1">
          <p className="text-[13px] font-medium text-zinc-500">{label}</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight text-zinc-900">{value}</p>
          {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
        </div>
      </CardContent>
    </Card>
  )
}

function PipelineTable({ pipeline }: { pipeline: ManagementDashboard['pipeline'] }) {
  if (pipeline.length === 0) {
    return <EmptyState icon={<Filter />} title="Pipeline vacío" description="No hay oportunidades activas en el pipeline." />
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-100 text-left">
            <th className="h-10 px-4 text-xs font-medium uppercase tracking-wide text-zinc-500">Etapa</th>
            <th className="h-10 px-4 text-xs font-medium uppercase tracking-wide text-zinc-500">Cantidad</th>
            <th className="h-10 px-4 text-xs font-medium uppercase tracking-wide text-zinc-500">Monto estimado</th>
          </tr>
        </thead>
        <tbody>
          {pipeline.map((stage) => (
            <tr key={stage.stage_id} className="border-b border-zinc-100 last:border-0">
              <td className="px-4 py-3">
                <Badge style={{ backgroundColor: `${stage.color}14`, color: stage.color ?? undefined, boxShadow: `inset 0 0 0 1px ${stage.color}33` }}>
                  {stage.stage_name}
                </Badge>
              </td>
              <td className="px-4 py-3 font-medium">{stage.count}</td>
              <td className="px-4 py-3">{formatMoney(stage.estimated_amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TopPerformers({ performers }: { performers: ManagementDashboard['top_performers'] }) {
  if (performers.length === 0) {
    return <EmptyState icon={<Trophy />} title="Sin ventas cerradas" description="Aún no hay oportunidades ganadas este mes." />
  }
  return (
    <div className="space-y-3">
      {performers.map((p, i) => (
        <div key={p.user_id} className="flex items-center gap-3 rounded-lg border border-zinc-100 p-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-100 text-xs font-semibold text-zinc-600">
            {i + 1}
          </span>
          <div className="flex-1">
            <p className="font-medium text-zinc-900">{p.full_name}</p>
            <p className="text-xs text-zinc-500">{p.won_count} oportunidad{p.won_count === 1 ? '' : 'es'} ganada{p.won_count === 1 ? '' : 's'}</p>
          </div>
          <span className="font-semibold text-zinc-900">{formatMoney(p.won_amount)}</span>
        </div>
      ))}
    </div>
  )
}

function TopProducts({ products }: { products: ManagementDashboard['top_products'] }) {
  if (products.length === 0) {
    return <EmptyState icon={<BarChart3 />} title="Sin productos cotizados" description="Aún no hay productos en cotizaciones." />
  }
  return (
    <div className="space-y-3">
      {products.map((p, i) => (
        <div key={p.product_id} className="flex items-center gap-3 rounded-lg border border-zinc-100 p-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-100 text-xs font-semibold text-zinc-600">
            {i + 1}
          </span>
          <div className="flex-1">
            <p className="font-medium text-zinc-900">{p.product_name}</p>
            <p className="text-xs text-zinc-500">{p.quote_count} cotización{p.quote_count === 1 ? '' : 'es'}</p>
          </div>
          <span className="font-semibold text-zinc-900">{formatMoney(p.total_amount)}</span>
        </div>
      ))}
    </div>
  )
}

export default function ManagementDashboardPage() {
  const { can } = usePermissions()
  const canRecalculate = can(P.DASHBOARD_MANAGEMENT)
  const queryClient = useQueryClient()

  const dashboardQ = useQuery({
    queryKey: ['dashboard', 'management'],
    queryFn: () => dashboardService.management(),
  })

  const recalculateM = useMutation({
    mutationFn: () => dashboardService.management(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dashboard', 'management'] }),
  })

  const d = dashboardQ.data

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard gerencial"
        description={d ? `Actualizado el ${formatDateTime(d.generated_at)}` : 'Métricas comerciales y rendimiento del equipo.'}
        actions={
          canRecalculate && (
            <Button variant="outline" onClick={() => recalculateM.mutate()} disabled={recalculateM.isPending || dashboardQ.isLoading}>
              {recalculateM.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : <RefreshCw className="mr-2 size-4" />}
              Actualizar
            </Button>
          )
        }
      />

      {d && (
        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-6">
          <motion.div variants={fadeUp} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Ventas este mes" value={formatMoney(d.sales_this_month)} icon={DollarSign} tone="success" hint={`Mes pasado: ${formatMoney(d.sales_last_month)}`} />
            <KpiCard label="Nuevos clientes" value={d.new_clients_this_month} icon={Users} tone="brand" hint={`Mes pasado: ${d.new_clients_last_month}`} />
            <KpiCard label="Tasa de conversión" value={`${d.conversion.conversion_rate}%`} icon={TrendingUp} tone="warning" hint={`${d.conversion.converted_to_client} de ${d.conversion.total_prospects} prospectos`} />
            <KpiCard label="Pipeline total" value={formatMoney(d.pipeline.reduce((acc, s) => acc + s.estimated_amount, 0))} icon={Filter} tone="neutral" hint={`${d.pipeline.reduce((acc, s) => acc + s.count, 0)} oportunidades`} />
          </motion.div>

          <div className="grid gap-6 lg:grid-cols-2">
            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Filter className="size-5 text-zinc-500" />
                    Pipeline por etapa
                  </CardTitle>
                  <CardDescription>Oportunidades activas distribuidas por etapa.</CardDescription>
                </CardHeader>
                <CardContent>
                  <PipelineTable pipeline={d.pipeline} />
                </CardContent>
              </Card>
            </motion.div>

            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Trophy className="size-5 text-zinc-500" />
                    Top vendedores
                  </CardTitle>
                  <CardDescription>Vendedores con más ventas cerradas este mes.</CardDescription>
                </CardHeader>
                <CardContent>
                  <TopPerformers performers={d.top_performers} />
                </CardContent>
              </Card>
            </motion.div>

            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="size-5 text-zinc-500" />
                    Top productos cotizados
                  </CardTitle>
                  <CardDescription>Productos más cotizados por monto.</CardDescription>
                </CardHeader>
                <CardContent>
                  <TopProducts products={d.top_products} />
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </motion.div>
      )}
    </PageContainer>
  )
}
