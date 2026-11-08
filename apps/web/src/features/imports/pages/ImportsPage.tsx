import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileSpreadsheet, Upload, AlertCircle, CheckCircle2, Clock, FileX } from 'lucide-react'
import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { EmptyState } from '@/shared/ui/feedback'
import { PageContainer, PageHeader } from '@/shared/ui/page'

import { importsKeys, importsService, type ImportPreview } from '../api/imports-service'

const STATUS_LABEL: Record<string, string> = {
  PENDING: 'Pendiente',
  PROCESSING: 'Procesando',
  COMPLETED: 'Completado',
  COMPLETED_WITH_ERRORS: 'Completado con errores',
  FAILED: 'Fallido',
}

const STATUS_TONE: Record<string, 'neutral' | 'brand' | 'success' | 'warning' | 'danger'> = {
  PENDING: 'neutral',
  PROCESSING: 'brand',
  COMPLETED: 'success',
  COMPLETED_WITH_ERRORS: 'warning',
  FAILED: 'danger',
}

export default function ImportsPage() {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)

  const previewMutation = useMutation({
    mutationFn: (f: File) => importsService.preview(f),
    onSuccess: setPreview,
    onError: (e) => toast.error(errorMessage(e)),
  })

  const importMutation = useMutation({
    mutationFn: (f: File) => importsService.import(f),
    onSuccess: () => {
      toast.success('Importación completada')
      setFile(null)
      setPreview(null)
      queryClient.invalidateQueries({ queryKey: importsKeys.jobs() })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const jobsQuery = useQuery({
    queryKey: importsKeys.jobs(),
    queryFn: () => importsService.list(),
  })

  const handleFile = (f: File | null) => {
    if (!f) return
    if (!f.name.endsWith('.xlsx')) {
      toast.error('Solo se aceptan archivos .xlsx')
      return
    }
    setFile(f)
    previewMutation.mutate(f)
  }

  return (
    <PageContainer>
      <PageHeader
        title="Importaciones"
        description="Importa el Excel FOR-VEN-001 al CRM."
      />

      <Card className="p-6">
        <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-300 p-8 text-center">
          <FileSpreadsheet className="mb-3 size-10 text-zinc-400" />
          <p className="text-sm font-medium text-zinc-900">Arrastra aquí el Excel FOR-VEN-001</p>
          <p className="mt-1 text-xs text-muted-foreground">O selecciona el archivo desde tu equipo.</p>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => inputRef.current?.click()}
            loading={previewMutation.isPending}
          >
            <Upload className="mr-2 size-4" />
            Seleccionar archivo
          </Button>
        </div>

        {preview && (
          <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-900">{preview.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {preview.total_rows} filas · {preview.valid_rows} válidas · {preview.invalid_rows} con errores
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => { setFile(null); setPreview(null) }}>
                  Cancelar
                </Button>
                <Button
                  onClick={() => file && importMutation.mutate(file)}
                  loading={importMutation.isPending}
                  disabled={preview.invalid_rows > 0}
                >
                  <CheckCircle2 className="mr-2 size-4" />
                  Importar
                </Button>
              </div>
            </div>

            {preview.invalid_rows > 0 && (
              <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                <div className="flex items-center gap-2 font-medium">
                  <AlertCircle className="size-4" />
                  Corrige los errores antes de importar
                </div>
              </div>
            )}

            <div className="max-h-80 overflow-auto rounded-lg border border-zinc-200">
              <table className="w-full text-xs">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="px-3 py-2 text-left">Fila</th>
                    <th className="px-3 py-2 text-left">RUC</th>
                    <th className="px-3 py-2 text-left">Razón social</th>
                    <th className="px-3 py-2 text-left">Estado</th>
                    <th className="px-3 py-2 text-left">Errores</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {preview.rows.map((row) => (
                    <tr key={row.row_number} className={row.valid ? '' : 'bg-red-50/50'}>
                      <td className="px-3 py-2">{row.row_number}</td>
                      <td className="px-3 py-2">{row.ruc}</td>
                      <td className="px-3 py-2">{row.name}</td>
                      <td className="px-3 py-2">
                        {row.valid ? (
                          <span className="inline-flex items-center gap-1 text-green-700">
                            <CheckCircle2 className="size-3" /> Válida
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-700">
                            <FileX className="size-3" /> Con errores
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-red-600">
                        {row.errors.join(', ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      <h2 className="mt-8 text-lg font-semibold text-zinc-900">Historial de importaciones</h2>
      <Card className="mt-4 p-0">
        {jobsQuery.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">Cargando historial…</p>
        ) : (jobsQuery.data?.length ?? 0) === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Clock />}
              title="Sin importaciones"
              description="Aún no se ha importado ningún Excel."
            />
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {jobsQuery.data?.map((job) => (
              <div key={job.id} className="flex items-start justify-between p-4 text-sm">
                <div>
                  <p className="font-medium text-zinc-900">{job.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {job.processed_rows} / {job.total_rows} filas · {job.created_prospects} prospectos · {job.created_interactions} interacciones
                  </p>
                </div>
                <Badge tone={STATUS_TONE[job.status]}>{STATUS_LABEL[job.status]}</Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </PageContainer>
  )
}
