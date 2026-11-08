import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api, type Schemas, unwrap } from '@/shared/api/client'
import { ApiError, errorMessage } from '@/shared/api/errors'
import { P, usePermissions } from '@/shared/auth/permissions'
import { fadeUp, stagger } from '@/shared/lib/motion'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'
import { DataListSkeleton } from '@/shared/ui/data-list'
import { ErrorState } from '@/shared/ui/feedback'
import { Input } from '@/shared/ui/input'
import { Switch } from '@/shared/ui/menus'
import { FormField, PageContainer, PageHeader } from '@/shared/ui/page'

type Group = Schemas['SettingGroup']
type Value = string | number | boolean | number[]

interface FieldSchema {
  title?: string
  type?: string
  minimum?: number
  maximum?: number
  anyOf?: { type?: string }[]
  items?: { type?: string }
}

const DESCRIPTIONS: Record<string, string> = {
  general: 'Datos de la empresa y regionales.',
  prospects: 'Reglas para el registro de prospectos y detección de duplicados.',
  alerts: 'Umbrales que usarán las alertas automáticas para evitar prospectos olvidados.',
}

function kindOf(f: FieldSchema): 'boolean' | 'number' | 'list' | 'text' {
  if (f.type === 'boolean') return 'boolean'
  if (f.type === 'array') return 'list'
  if (f.type === 'integer' || f.type === 'number' || f.anyOf?.some((a) => a.type === 'number')) return 'number'
  return 'text'
}

function SettingGroupCard({ group, readOnly }: { group: Group; readOnly: boolean }) {
  const qc = useQueryClient()
  const fields = group.fields as Record<string, FieldSchema>
  const [draft, setDraft] = useState<Record<string, string | boolean>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})

  const toDraft = () =>
    Object.fromEntries(
      Object.entries(group.value as Record<string, Value>).map(([k, v]) => [k, typeof v === 'boolean' ? v : Array.isArray(v) ? v.join(', ') : String(v)]),
    )
  useEffect(() => setDraft(toDraft()), [group]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {}
      for (const [k, f] of Object.entries(fields)) {
        const v = draft[k]
        const kind = kindOf(f)
        payload[k] =
          kind === 'number' ? Number(v) : kind === 'list' ? String(v).split(',').map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n)) : v
      }
      return unwrap(api.PUT('/api/v1/settings/{key}', { params: { path: { key: group.key } }, body: payload as never /* cuerpo libre validado por el backend */ }))
    },
    onSuccess: () => {
      setErrors({})
      toast.success(`${group.label}: cambios guardados`)
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (e) => {
      if (e instanceof ApiError && e.fieldErrors.length) {
        setErrors(Object.fromEntries(e.fieldErrors.map((f) => [f.field.split('.')[0], f.message])))
      } else toast.error(errorMessage(e))
    },
  })

  const dirty = JSON.stringify(draft) !== JSON.stringify(toDraft())

  return (
    <motion.div variants={fadeUp}>
      <Card>
        <CardHeader>
          <div>
            <CardTitle>{group.label}</CardTitle>
            <CardDescription>{DESCRIPTIONS[group.key]}</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault()
              save.mutate()
            }}
          >
            <div className="grid gap-5 sm:grid-cols-2">
              {Object.entries(fields).map(([key, f]) => {
                const kind = kindOf(f)
                if (kind === 'boolean')
                  return (
                    <label key={key} className="flex items-center justify-between gap-4 rounded-lg border border-zinc-200 p-3 sm:col-span-2">
                      <span className="text-sm text-zinc-800">{f.title}</span>
                      <Switch checked={!!draft[key]} disabled={readOnly} onCheckedChange={(v) => setDraft((d) => ({ ...d, [key]: v }))} />
                    </label>
                  )
                return (
                  <FormField
                    key={key}
                    label={f.title ?? key}
                    error={errors[key]}
                    hint={kind === 'list' ? 'Separa los valores con comas.' : f.minimum !== undefined ? `Entre ${f.minimum} y ${f.maximum ?? '∞'}` : undefined}
                  >
                    {(p) => (
                      <Input
                        {...p}
                        disabled={readOnly}
                        inputMode={kind === 'number' ? 'decimal' : undefined}
                        className={kind === 'number' ? 'tabular' : undefined}
                        value={String(draft[key] ?? '')}
                        onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
                      />
                    )}
                  </FormField>
                )
              })}
            </div>
            {!readOnly && (
              <div className="flex justify-end gap-2 border-t border-zinc-100 pt-4">
                <Button type="button" variant="ghost" disabled={!dirty} onClick={() => { setDraft(toDraft()); setErrors({}) }}>
                  Descartar
                </Button>
                <Button type="submit" disabled={!dirty} loading={save.isPending}>
                  Guardar
                </Button>
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default function SettingsPage() {
  const { can } = usePermissions()
  const settings = useQuery({ queryKey: ['settings'], queryFn: () => unwrap(api.GET('/api/v1/settings')) })

  return (
    <PageContainer className="max-w-4xl">
      <PageHeader title="Configuración" description="Parámetros generales del CRM. Cada cambio queda registrado en auditoría." />
      {settings.isPending ? (
        <Card><DataListSkeleton rows={4} /></Card>
      ) : settings.isError ? (
        <ErrorState error={settings.error} onRetry={() => settings.refetch()} />
      ) : (
        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-6">
          {settings.data.map((g) => (
            <SettingGroupCard key={g.key} group={g} readOnly={!can(P.SETTINGS_MANAGE)} />
          ))}
        </motion.div>
      )}
    </PageContainer>
  )
}
