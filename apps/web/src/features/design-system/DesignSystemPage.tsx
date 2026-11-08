import { CircleDollarSign, FileText, Plus, UsersRound } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { toast } from 'sonner'
import { stagger } from '@/shared/lib/motion'
import { Badge, ColorBadge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'
import { DataListSkeleton } from '@/shared/ui/data-list'
import { EmptyState, ErrorState, ForbiddenState, NoResults } from '@/shared/ui/feedback'
import { Input } from '@/shared/ui/input'
import { Checkbox, Select, Switch, Tooltip } from '@/shared/ui/menus'
import { KpiCard, Logo } from '@/shared/ui/misc'
import { FormField, PageContainer, PageHeader, Segmented } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'

const BRAND = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950']

/** Página interna (solo desarrollo) para revisar componentes, estados y tokens de diseño. */
export default function DesignSystemPage() {
  const [seg, setSeg] = useState('a')
  const [sheet, setSheet] = useState(false)
  return (
    <PageContainer className="space-y-8">
      <PageHeader title="Sistema de diseño" description="Tokens, componentes y estados del CRM (solo visible en desarrollo)." />

      <Card>
        <CardHeader><CardTitle>Marca</CardTitle></CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-wrap items-center gap-6">
            <Logo className="h-10 w-auto" />
            <div className="rounded-lg bg-ink-950 p-4"><Logo onDark className="h-8 w-auto" /></div>
            <Logo variant="mark" className="size-10" />
            <div className="rounded-lg bg-ink-950 p-3"><Logo variant="mark" onDark className="size-8" /></div>
          </div>
          <div className="grid grid-cols-6 gap-2 sm:grid-cols-11">
            {BRAND.map((s) => (
              <div key={s} className="space-y-1">
                <div className="h-12 rounded-md ring-1 ring-black/5" style={{ backgroundColor: `var(--color-brand-${s})` }} />
                <p className="text-center text-[11px] text-zinc-500">{s}{s === '600' && ' ★'}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">★ #E03E0F oficial. Botones usan #D4390D (contraste AA con texto blanco).</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Botones y badges</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button><Plus /> Primario</Button>
            <Button variant="secondary">Secundario</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Eliminar</Button>
            <Button loading>Guardando</Button>
            <Button variant="link">Enlace</Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(['neutral', 'brand', 'success', 'warning', 'danger', 'info', 'dark'] as const).map((t) => <Badge key={t} tone={t} dot>{t}</Badge>)}
            <ColorBadge color="#16A34A">Interés alto</ColorBadge>
            <ColorBadge color="#D97706">Interés regular</ColorBadge>
            <ColorBadge color="#71717A">Interés bajo</ColorBadge>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => toast.success('Guardado correctamente')}>Toast éxito</Button>
            <Button variant="outline" onClick={() => toast.error('Ya existe un prospecto con este RUC.')}>Toast error</Button>
            <Button variant="outline" onClick={() => setSheet(true)}>Abrir panel</Button>
            <Tooltip content="Tooltip de ejemplo"><Button variant="outline">Tooltip</Button></Tooltip>
          </div>
        </CardContent>
      </Card>

      <motion.div variants={stagger} initial="hidden" animate="show" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Ventas del mes" value="S/ 48,250.00" hint="+12% vs. mes anterior" icon={<CircleDollarSign />} accent />
        <KpiCard label="Cotizaciones" value="37" hint="9 sin respuesta" icon={<FileText />} />
        <KpiCard label="Prospectos activos" value="128" icon={<UsersRound />} />
        <KpiCard label="Conversión" value="18.4%" hint="Prospecto → cliente" />
      </motion.div>

      <Card>
        <CardHeader><CardTitle>Formularios</CardTitle></CardHeader>
        <CardContent className="grid gap-5 sm:grid-cols-2">
          <FormField label="Razón social" required>{(p) => <Input {...p} placeholder="Ej. Distribuidora Andina SAC" />}</FormField>
          <FormField label="RUC" required error="El RUC debe tener 11 dígitos.">{(p) => <Input {...p} defaultValue="2060" />}</FormField>
          <FormField label="Origen" optional>{(p) => <Select {...p} onValueChange={() => {}} options={[{ value: 'web', label: 'Página web' }, { value: 'ref', label: 'Referido' }]} />}</FormField>
          <div className="flex items-center gap-6 pt-6">
            <label className="flex items-center gap-2 text-sm"><Checkbox defaultChecked /> Contacto principal</label>
            <label className="flex items-center gap-2 text-sm"><Switch defaultChecked /> Activo</label>
          </div>
          <Segmented value={seg} onChange={setSeg} options={[{ value: 'a', label: 'Hoy' }, { value: 'b', label: 'Semana' }, { value: 'c', label: 'Mes' }]} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card><DataListSkeleton rows={3} /></Card>
        <Card><EmptyState title="Sin prospectos todavía" description="Registra el primero en segundos." action={<Button size="sm"><Plus /> Nuevo prospecto</Button>} /></Card>
        <Card><NoResults onClear={() => {}} /></Card>
        <Card><ErrorState error={null} onRetry={() => {}} /></Card>
        <Card className="lg:col-span-2"><ForbiddenState /></Card>
      </div>

      <Sheet open={sheet} onOpenChange={setSheet}>
        <SheetContent title="Panel de ejemplo" description="Derecha en escritorio, desde abajo en celular." footer={<Button onClick={() => setSheet(false)}>Listo</Button>}>
          <p className="text-sm text-zinc-600">Contenido del panel.</p>
        </SheetContent>
      </Sheet>
    </PageContainer>
  )
}
