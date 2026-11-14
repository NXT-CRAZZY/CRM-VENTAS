import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Lock, Plus, ShieldCheck, Trash2, Users } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { P, usePermissions } from '@/shared/auth/permissions'
import { fadeUp } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { DataListSkeleton } from '@/shared/ui/data-list'
import { ErrorState } from '@/shared/ui/feedback'
import { Checkbox, Select } from '@/shared/ui/menus'
import { ConfirmDialog } from '@/shared/ui/misc'
import { PageContainer, PageHeader } from '@/shared/ui/page'
import { type Role, rolesKeys, rolesService, usePermissionGroups, useRoles } from '../api/roles-service'
import { CreateRoleDialog } from '../components/CreateRoleDialog'

export default function RolesPage() {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const canManage = can(P.ROLES_MANAGE)
  const roles = useRoles()
  const groups = usePermissionGroups()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Set<string>>(new Set())
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const selected: Role | undefined = roles.data?.find((r) => r.id === selectedId) ?? roles.data?.[0]
  useEffect(() => setDraft(new Set(selected?.permissions)), [selected])

  const locked = !canManage || selected?.code === 'ADMIN'
  const dirty = useMemo(
    () => !!selected && (draft.size !== selected.permissions.length || selected.permissions.some((p) => !draft.has(p))),
    [draft, selected],
  )

  const save = useMutation({
    mutationFn: () => rolesService.update(selected!.id, { permissions: [...draft] }),
    onSuccess: () => {
      toast.success('Permisos actualizados', { description: 'Los usuarios con este rol verán los cambios al renovar su sesión.' })
      qc.invalidateQueries({ queryKey: rolesKeys.roles })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const remove = useMutation({
    mutationFn: () => rolesService.remove(selected!.id),
    onSuccess: () => {
      toast.success('Rol eliminado')
      setSelectedId(null)
      qc.invalidateQueries({ queryKey: rolesKeys.roles })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const toggle = (code: string, on: boolean) =>
    setDraft((d) => {
      const n = new Set(d)
      if (on) n.add(code)
      else n.delete(code)
      return n
    })

  if (roles.isError || groups.isError) return <PageContainer><ErrorState error={roles.error ?? groups.error} onRetry={() => roles.refetch()} /></PageContainer>

  return (
    <PageContainer>
      <PageHeader
        title="Roles y permisos"
        description="Define qué puede ver y hacer cada perfil. Los permisos se validan siempre en el servidor."
        actions={canManage && (
          <Button onClick={() => setCreating(true)}>
            <Plus /> Nuevo rol
          </Button>
        )}
      />

      {roles.isPending || groups.isPending ? (
        <Card><DataListSkeleton /></Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          {/* Lista de roles */}
          <div className="lg:hidden">
            <Select
              value={selected?.id}
              onValueChange={setSelectedId}
              options={roles.data.map((r) => ({ value: r.id, label: r.name }))}
            />
          </div>
          <div className="hidden space-y-2 lg:block">
            {roles.data.map((r) => {
              const active = r.id === selected?.id
              return (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setSelectedId(r.id)}
                  className={cn(
                    'relative w-full rounded-lg border p-4 text-left transition-all duration-150',
                    active ? 'border-brand-300 bg-card shadow-sm' : 'border-zinc-200/80 bg-card/60 hover:border-zinc-300 hover:bg-card',
                  )}
                >
                  {active && <motion.span layoutId="role-active" className="absolute inset-y-3 left-0 w-[3px] rounded-r-full bg-brand-600" />}
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-zinc-900">{r.name}</span>
                    {r.is_system && <Badge>Sistema</Badge>}
                  </div>
                  <p className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1"><Users className="size-3.5" />{r.user_count}</span>
                    <span className="inline-flex items-center gap-1"><ShieldCheck className="size-3.5" />{r.permissions.length} permisos</span>
                  </p>
                </button>
              )
            })}
          </div>

          {/* Matriz de permisos */}
          {selected && (
            <Card>
              <div className="flex flex-col gap-3 border-b border-zinc-100 p-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-base font-semibold text-zinc-900">{selected.name}</h2>
                  <p className="mt-0.5 text-sm text-muted-foreground">{selected.description ?? 'Sin descripción'}</p>
                </div>
                {canManage && !selected.is_system && (
                  <Button variant="ghost" size="sm" className="text-red-700 hover:bg-red-50 hover:text-red-800" onClick={() => setDeleting(true)}>
                    <Trash2 /> Eliminar rol
                  </Button>
                )}
              </div>
              {selected.code === 'ADMIN' && (
                <p className="mx-5 mt-4 flex items-center gap-2 rounded-md bg-zinc-50 px-3 py-2 text-[13px] text-zinc-600">
                  <Lock className="size-3.5" /> El Administrador siempre tiene todos los permisos.
                </p>
              )}
              <div className="divide-y divide-zinc-100">
                {groups.data.map((g) => (
                  <motion.div key={g.module} variants={fadeUp} initial="hidden" animate="show" className="grid gap-3 p-5 sm:grid-cols-[180px_1fr]">
                    <p className="text-sm font-medium text-zinc-900">{g.module}</p>
                    <div className="grid gap-2.5 sm:grid-cols-2">
                      {g.permissions.map((perm) => (
                        <label
                          key={perm.code}
                          className={cn('flex items-start gap-2.5 text-sm text-zinc-700', locked ? 'cursor-default' : 'cursor-pointer')}
                        >
                          <Checkbox
                            className="mt-0.5"
                            checked={draft.has(perm.code)}
                            disabled={locked}
                            onCheckedChange={(v) => toggle(perm.code, v === true)}
                          />
                          {perm.name}
                        </label>
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Barra flotante de guardado */}
      <AnimatePresence>
        {dirty && !locked && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-x-4 bottom-20 z-30 mx-auto flex max-w-xl items-center justify-between gap-3 rounded-xl bg-ink-900 px-4 py-3 text-sm text-white shadow-lg lg:bottom-6"
          >
            <span>Tienes cambios sin guardar</span>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" className="text-zinc-300 hover:bg-card/10 hover:text-white" onClick={() => setDraft(new Set(selected?.permissions))}>
                Descartar
              </Button>
              <Button size="sm" loading={save.isPending} onClick={() => save.mutate()}>
                Guardar
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <CreateRoleDialog
        open={creating}
        onOpenChange={setCreating}
        onCreated={(r) => {
          qc.invalidateQueries({ queryKey: rolesKeys.roles })
          setSelectedId(r.id)
        }}
      />
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title={`¿Eliminar el rol “${selected?.name}”?`}
        description="Solo es posible si ningún usuario lo tiene asignado."
        confirmLabel="Eliminar"
        destructive
        onConfirm={() => remove.mutateAsync()}
      />
    </PageContainer>
  )
}
