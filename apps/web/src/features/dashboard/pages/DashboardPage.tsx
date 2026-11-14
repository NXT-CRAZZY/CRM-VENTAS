import {
  ArrowRight,
  CheckCircle2,
  Clock,
  ListChecks,
  Package,
  UsersRound,
  AlertTriangle,
  Flame,
  Phone,
  UserPlus,
} from 'lucide-react'
import { motion } from 'motion/react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useSessionStore } from '@/shared/auth/session-store'
import { greeting, formatDateTime } from '@/shared/lib/format'
import { pendingTabFor } from '@/features/tasks/model/task-tabs'
import { fadeUp, stagger } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'
import { PageContainer, PageHeader } from '@/shared/ui/page'

import { dashboardService } from '../api/dashboard-service'

function KpiCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = 'neutral',
  href,
}: {
  label: string
  value: number
  hint?: string
  icon: React.ElementType
  tone?: 'neutral' | 'brand' | 'warning' | 'danger'
  href?: string
}) {
  const content = (
    <Card className={cn('transition-all duration-200 hover:shadow-md', href && 'cursor-pointer hover:-translate-y-0.5')}>
      <CardContent className="flex items-start gap-4 p-5">
        <span
          className={cn(
            'rounded-lg p-2.5 ring-1 ring-inset',
            tone === 'brand' && 'bg-brand-50 text-brand-600 ring-brand-100',
            tone === 'warning' && 'bg-amber-50 text-amber-600 ring-amber-100',
            tone === 'danger' && 'bg-red-50 text-red-600 ring-red-100',
            tone === 'neutral' && 'bg-zinc-50 text-zinc-500 ring-zinc-200',
          )}
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
  if (href) return <Link to={href}>{content}</Link>
  return content
}

export function DashboardPage() {
  const user = useSessionStore((s) => s.user)
  const { can } = usePermissions()
  const firstName = user?.full_name.split(' ')[0] ?? ''

  const dashboardQ = useQuery({
    queryKey: ['dashboard', 'sales'],
    queryFn: () => dashboardService.sales(),
  })

  const shortcuts = [
    { to: '/productos', label: 'Catálogo de productos', hint: 'Productos y servicios con precios vigentes', permission: P.PRODUCTS_READ, icon: Package },
    { to: '/admin/usuarios', label: 'Equipo comercial', hint: 'Crea usuarios y asigna roles', permission: P.USERS_MANAGE, icon: UsersRound },
    { to: '/admin/catalogos', label: 'Catálogos', hint: 'Formas de contacto, interés, motivos de pérdida…', permission: P.CATALOGS_MANAGE, icon: ListChecks },
  ].filter((s) => can(s.permission))

  const d = dashboardQ.data

  return (
    <PageContainer>
      <PageHeader
        title={`${greeting()}, ${firstName}`}
        description="Resumen de tu actividad comercial de hoy."
      />

      {d && (
        <motion.div variants={stagger} initial="hidden" animate="show" className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <motion.div variants={fadeUp}>
            <KpiCard label="Tareas hoy" value={d.tasks_today} icon={ListChecks} tone="brand" href={`/tareas?due=today&assignee=${user?.id ?? ""}`} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <KpiCard label="Tareas vencidas" value={d.tasks_overdue} icon={AlertTriangle} tone="danger" href={`/tareas?due=overdue&assignee=${user?.id ?? ""}`} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <KpiCard label="Nuevos últimos 7 días" value={d.new_prospects_this_week} icon={UserPlus} tone="neutral" href="/prospectos?created_since_days=7" />
          </motion.div>
          <motion.div variants={fadeUp}>
            <KpiCard label="Seguimientos hoy" value={d.follow_ups_today} icon={Phone} tone="brand" href="/prospectos?next_action_today=true" />
          </motion.div>
          <motion.div variants={fadeUp}>
            <KpiCard label={`Sin contacto > ${d.no_contact_days} días`} value={d.prospects_without_contact} icon={Clock} tone="warning" href={`/prospectos?without_contact_days=${d.no_contact_days}`} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <KpiCard label="Alto interés" value={d.high_interest_prospects} icon={Flame} tone="brand" href="/prospectos?interest_level_code=ALTO&relationship_type=PROSPECTO" />
          </motion.div>
        </motion.div>
      )}

      <div className="mb-8 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Próximas acciones</CardTitle>
            <CardDescription>Tareas programadas.</CardDescription>
          </CardHeader>
          <CardContent>
            {!d || dashboardQ.isLoading ? (
              <p className="text-sm text-muted-foreground">Cargando…</p>
            ) : d.upcoming_actions.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                <CheckCircle2 className="mx-auto mb-2 size-8 text-zinc-300" />
                <p>No hay acciones pendientes. ¡Buen trabajo!</p>
              </div>
            ) : (
              <div className="divide-y divide-zinc-100">
                {d.upcoming_actions.map((a) => (
                  <div key={a.task_id} className="flex items-start gap-3 py-3 text-sm">
                    <div className="mt-0.5 size-2 rounded-full bg-brand-500" />
                    <div className="flex-1">
                      <p className="font-medium text-zinc-900">{a.prospect_name}</p>
                      <p className="text-zinc-600">{a.action_type}</p>
                      {a.due_at && <p className="text-xs text-muted-foreground">{formatDateTime(a.due_at)}</p>}
                    </div>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/tareas?due=${pendingTabFor(a.due_at)}&task=${a.task_id}`}>Ver tarea</Link>
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Accesos rápidos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button className="w-full justify-start gap-2" asChild>
              <Link to="/prospectos?action=new">
                <UserPlus className="size-4" /> Nuevo prospecto
              </Link>
            </Button>
            <Button variant="outline" className="w-full justify-start gap-2" asChild>
              <Link to="/prospectos">
                <UsersRound className="size-4" /> Ver prospectos
              </Link>
            </Button>
            {can(P.PRODUCTS_READ) && (
              <Button variant="outline" className="w-full justify-start gap-2" asChild>
                <Link to="/productos">
                  <Package className="size-4" /> Catálogo
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      {shortcuts.length > 0 && (
        <motion.div variants={stagger} initial="hidden" animate="show" className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {shortcuts.map(({ to, label, hint, icon: Icon }) => (
            <motion.div key={to} variants={fadeUp}>
              <Link
                to={to}
                className="group flex items-center gap-4 rounded-lg border border-zinc-200/80 bg-card p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md"
              >
                <span className="rounded-lg bg-brand-50 p-2.5 text-brand-600 ring-1 ring-inset ring-brand-100">
                  <Icon className="size-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-zinc-900">{label}</span>
                  <span className="block truncate text-[13px] text-muted-foreground">{hint}</span>
                </span>
                <ArrowRight className="size-4 text-zinc-300 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-brand-600" />
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}

    </PageContainer>
  )
}
