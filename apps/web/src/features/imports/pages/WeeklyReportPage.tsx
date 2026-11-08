import { useQuery } from '@tanstack/react-query'
import { BarChart3, Calendar, Download, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { formatMoney } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Input } from '@/shared/ui/input'
import { PageContainer, PageHeader } from '@/shared/ui/page'

import { importsKeys, importsService } from '../api/imports-service'

export default function WeeklyReportPage() {
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0])

  const reportQuery = useQuery({
    queryKey: importsKeys.weeklyReport(date),
    queryFn: () => importsService.weeklyReport(date),
  })

  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await importsService.exportWeeklyReport(date)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `FOR-VEN-001_${date}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.success('Excel descargado')
    } catch {
      toast.error('No se pudo descargar el Excel')
    } finally {
      setExporting(false)
    }
  }

  const report = reportQuery.data

  return (
    <PageContainer>
      <PageHeader
        title="Informe semanal"
        description="Indicadores de ventas compatibles con el Excel FOR-VEN-001."
        actions={
          <Button variant="outline" onClick={handleExport} disabled={exporting || reportQuery.isLoading}>
            {exporting ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Download className="mr-2 size-4" />}
            Descargar Excel
          </Button>
        }
      />

      <div className="mb-6 flex max-w-xs items-center gap-3">
        <Calendar className="size-4 text-muted-foreground" />
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      {reportQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando informe…</p>
      ) : report ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard label="Cotizaciones hoy" value={report.quotes_today} />
            <MetricCard label="Cotizaciones del mes" value={report.quotes_month} />
            <MetricCard label="Ventas hoy" value={formatMoney(report.sales_today)} />
            <MetricCard label="Ventas del mes" value={formatMoney(report.sales_month)} />
            <MetricCard label="Ventas actualización hoy" value={formatMoney(report.sales_update_today)} />
            <MetricCard label="Ventas actualización mes" value={formatMoney(report.sales_update_month)} />
            <MetricCard label="Ventas nuevas hoy" value={formatMoney(report.sales_new_today)} />
            <MetricCard label="Ventas nuevas mes" value={formatMoney(report.sales_new_month)} />
            <MetricCard label="Nuevos clientes hoy" value={report.new_clients_today} />
            <MetricCard label="Nuevos clientes mes" value={report.new_clients_month} />
          </div>

          <Card className="p-0">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="px-4 py-3 text-left">Indicador</th>
                  <th className="px-4 py-3 text-right">Hoy</th>
                  <th className="px-4 py-3 text-right">Acumulado del mes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {report.rows.map((row) => (
                  <tr key={row.label}>
                    <td className="px-4 py-3 font-medium text-zinc-900">{row.label}</td>
                    <td className="px-4 py-3 text-right">{formatValue(row.today)}</td>
                    <td className="px-4 py-3 text-right">{formatValue(row.month)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No se pudo cargar el informe.</p>
      )}
    </PageContainer>
  )
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <BarChart3 className="size-5 text-brand-600" />
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold text-zinc-900">{value}</p>
        </div>
      </div>
    </Card>
  )
}

function formatValue(value: number) {
  if (Number.isInteger(value)) return value
  return formatMoney(value)
}
