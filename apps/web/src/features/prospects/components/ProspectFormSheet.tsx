import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Ban, Check, CircleAlert, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Controller, useFieldArray, useForm, type Resolver } from 'react-hook-form'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'
import { useActiveUsers } from '@/features/admin/users/api/users-service'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useSessionStore } from '@/shared/auth/session-store'
import { useCatalogBundle, type CatalogCode } from '@/shared/api/catalogs'
import { ApiError } from '@/shared/api/errors'
import { handleFormError } from '@/shared/lib/forms'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/menus'
import { Input, Textarea } from '@/shared/ui/input'
import { Select } from '@/shared/ui/menus'
import { FormField } from '@/shared/ui/page'
import { Sheet, SheetContent } from '@/shared/ui/sheet'

import { prospectsKeys, prospectsService, type DuplicateCheckResult, type Prospect } from '../api/prospects-service'
import { useTags } from '../api/prospects-service'
import { prospectContactSchema, prospectFormSchema, type ProspectFormValues } from '../model/schemas'

function emptyToNull<T>(v: T): T | null {
  if (v === '' || v === undefined) return null
  return v
}

function cleanContact(c: z.infer<typeof prospectContactSchema>) {
  return {
    full_name: c.full_name.trim(),
    position: emptyToNull(c.position),
    area: emptyToNull(c.area),
    email: emptyToNull(c.email),
    phone: emptyToNull(c.phone),
    whatsapp: emptyToNull(c.whatsapp),
    is_primary: c.is_primary,
    notes: emptyToNull(c.notes),
  }
}

function buildName(values: ProspectFormValues): string {
  if (values.person_type === 'NATURAL') {
    return `${values.first_name ?? ''} ${values.last_name ?? ''}`.trim()
  }
  return (values.legal_name ?? '').trim() || (values.trade_name ?? '').trim()
}

export function ProspectFormSheet({
  prospect,
  onClose,
}: {
  prospect: Prospect | 'new' | null
  onClose: () => void
}) {
  const { can } = usePermissions()
  const canAssign = can(P.PROSPECTS_ASSIGN)
  const isNew = prospect === 'new'
  const editing = prospect && prospect !== 'new' ? prospect : null
  const currentUser = useSessionStore((s) => s.user)
  const queryClient = useQueryClient()

  const catalogs = useCatalogBundle(['document_type', 'prospect_source', 'contact_channel', 'interest_level', 'priority'])
  const users = useActiveUsers(canAssign)
  const tags = useTags()

  const defaultValues: ProspectFormValues = useMemo(
    () =>
      editing
        ? {
            person_type: editing.person_type,
            document_type_id: editing.document_type?.id ?? '',
            document_number: editing.document_number ?? '',
            first_name: editing.first_name ?? '',
            last_name: editing.last_name ?? '',
            birth_date: editing.birth_date ?? '',
            legal_name: editing.legal_name ?? '',
            trade_name: editing.trade_name ?? '',
            email: editing.email ?? '',
            phone: editing.phone ?? '',
            phone_alt: editing.phone_alt ?? '',
            whatsapp: editing.whatsapp ?? '',
            address: editing.address ?? '',
            source_id: editing.source?.id ?? '',
            acquisition_channel_id: editing.acquisition_channel?.id ?? '',
            interest_level_id: editing.interest_level?.id ?? '',
            priority_id: editing.priority?.id ?? '',
            owner_id: editing.owner.id,
            notes: editing.notes ?? '',
            tags: editing.tags.map((t) => t.id),
            contacts: editing.contacts.map((c) => ({
              full_name: c.full_name,
              position: c.position ?? '',
              area: c.area ?? '',
              email: c.email ?? '',
              phone: c.phone ?? '',
              whatsapp: c.whatsapp ?? '',
              is_primary: c.is_primary,
              notes: c.notes ?? '',
            })),
          }
        : {
            person_type: 'NATURAL',
            document_type_id: '',
            document_number: '',
            first_name: '',
            last_name: '',
            birth_date: '',
            legal_name: '',
            trade_name: '',
            email: '',
            phone: '',
            phone_alt: '',
            whatsapp: '',
            address: '',
            source_id: '',
            acquisition_channel_id: '',
            interest_level_id: '',
            priority_id: '',
            owner_id: currentUser?.id ?? '',
            notes: '',
            tags: [],
            contacts: [],
          },
    [editing, currentUser?.id],
  )

  const form = useForm<ProspectFormValues>({
    resolver: zodResolver(prospectFormSchema) as Resolver<ProspectFormValues>,
    defaultValues,
  })
  const contacts = useFieldArray({ control: form.control, name: 'contacts' })

  useEffect(() => {
    if (!prospect) return
    form.reset(defaultValues)
  }, [prospect, defaultValues]) // eslint-disable-line react-hooks/exhaustive-deps

  // Sugerir tipo de documento según tipo de persona
  const personType = form.watch('person_type')
  useEffect(() => {
    const current = form.getValues('document_type_id')
    if (current) return
    const options = catalogs.data?.document_type ?? []
    const match = options.find((o) => o.code === (personType === 'NATURAL' ? 'DNI' : 'RUC'))
    if (match) form.setValue('document_type_id', match.id, { shouldValidate: false })
  }, [personType, catalogs.data?.document_type]) // eslint-disable-line react-hooks/exhaustive-deps

  const [duplicateResult, setDuplicateResult] = useState<DuplicateCheckResult | null>(null)
  const [duplicateKey, setDuplicateKey] = useState('')

  const duplicateCheck = useMutation({
    mutationFn: prospectsService.checkDuplicates,
    onSuccess: setDuplicateResult,
    onError: () => setDuplicateResult(null),
  })

  const watchDocument = form.watch('document_number')
  const watchEmail = form.watch('email')
  const watchPhone = form.watch('phone')
  const watchFirstName = form.watch('first_name')
  const watchLastName = form.watch('last_name')
  const watchLegalName = form.watch('legal_name')
  const watchTradeName = form.watch('trade_name')

  useEffect(() => {
    if (editing) {
      setDuplicateResult(null)
      return
    }
    const name = buildName(form.getValues())
    const key = [personType, watchDocument, watchEmail, watchPhone, name].join('|')
    if (!key.replace(/\|/g, '')) {
      setDuplicateResult(null)
      return
    }
    if (key === duplicateKey) return
    setDuplicateKey(key)

    const timer = setTimeout(() => {
      const values = form.getValues()
      const body = {
        person_type: values.person_type,
        document_number: values.document_number || null,
        email: values.email || null,
        phone: values.phone || null,
        name: buildName(values) || null,
      }
      if (body.document_number || body.email || body.phone || body.name) {
        duplicateCheck.mutate(body)
      }
    }, 400)
    return () => clearTimeout(timer)
  }, [
    editing,
    personType,
    watchDocument,
    watchEmail,
    watchPhone,
    watchFirstName,
    watchLastName,
    watchLegalName,
    watchTradeName,
    duplicateKey,
    form,
    duplicateCheck,
  ])

  const save = useMutation({
    mutationFn: async (values: ProspectFormValues) => {
      const base = {
        document_type_id: emptyToNull(values.document_type_id),
        document_number: emptyToNull(values.document_number),
        email: emptyToNull(values.email),
        phone: emptyToNull(values.phone),
        phone_alt: emptyToNull(values.phone_alt),
        whatsapp: emptyToNull(values.whatsapp),
        address: emptyToNull(values.address),
        source_id: emptyToNull(values.source_id),
        acquisition_channel_id: emptyToNull(values.acquisition_channel_id),
        interest_level_id: emptyToNull(values.interest_level_id),
        priority_id: emptyToNull(values.priority_id),
        notes: emptyToNull(values.notes),
        tags: values.tags ?? [],
        contacts: (values.contacts ?? []).map(cleanContact),
      }
      if (isNew) {
        return prospectsService.create({
          person_type: values.person_type,
          first_name: values.person_type === 'NATURAL' ? values.first_name : null,
          last_name: values.person_type === 'NATURAL' ? values.last_name : null,
          birth_date: emptyToNull(values.birth_date),
          legal_name: values.person_type === 'JURIDICA' ? values.legal_name : null,
          trade_name: values.person_type === 'JURIDICA' ? values.trade_name : null,
          owner_id: emptyToNull(values.owner_id),
          ...base,
        })
      }
      return prospectsService.update(editing!.id, {
        first_name: emptyToNull(values.first_name),
        last_name: emptyToNull(values.last_name),
        birth_date: emptyToNull(values.birth_date),
        legal_name: emptyToNull(values.legal_name),
        trade_name: emptyToNull(values.trade_name),
        owner_id: emptyToNull(values.owner_id),
        ...base,
      })
    },
    onSuccess: () => {
      toast.success(isNew ? 'Prospecto creado' : 'Cambios guardados')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
      onClose()
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === 'PROSPECT_DUPLICATE_DOCUMENT') {
        setDuplicateResult({ blocked: true, block_reason: e.message, matches: [] })
      }
      handleFormError(form, e, {
        PROSPECT_DUPLICATE_DOCUMENT: 'document_number',
        PROSPECT_INVALID_DOCUMENT: 'document_number',
      })
    },
  })

  const { errors } = form.formState
  const isBlocked = duplicateResult?.blocked ?? false

  const selectOptions = (code: CatalogCode) =>
    (catalogs.data?.[code] ?? []).map((o) => ({ value: o.id, label: o.name }))

  return (
    <Sheet open={!!prospect} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        title={isNew ? 'Nuevo prospecto' : 'Editar prospecto'}
        description={isNew ? 'Registro rápido de persona natural o jurídica.' : editing?.display_name}
        footer={
          <>
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" form="prospect-form" loading={save.isPending} disabled={isBlocked}>
              {isNew ? 'Crear prospecto' : 'Guardar cambios'}
            </Button>
          </>
        }
      >
        <form id="prospect-form" onSubmit={form.handleSubmit((d) => save.mutate(d as ProspectFormValues))} className="space-y-5" noValidate>
          {/* Tipo de persona */}
          <FormField label="Tipo de persona" required error={errors.person_type?.message}>
            {() => (
              <Controller
                control={form.control}
                name="person_type"
                render={({ field }) => (
                  <div className="grid grid-cols-2 gap-2">
                    {(['NATURAL', 'JURIDICA'] as const).map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => field.onChange(t)}
                        className={cn(
                          'flex items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors',
                          field.value === t
                            ? 'border-brand-300 bg-brand-50 text-brand-800'
                            : 'border-zinc-200 bg-card text-zinc-700 hover:bg-zinc-50',
                        )}
                      >
                        {field.value === t && <Check className="size-4" />}
                        {t === 'NATURAL' ? 'Natural' : 'Jurídica'}
                      </button>
                    ))}
                  </div>
                )}
              />
            )}
          </FormField>

          {/* Documento */}
          <div className="grid gap-5 sm:grid-cols-[140px_1fr]">
            <FormField label="Tipo doc." error={errors.document_type_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="document_type_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value}
                      onValueChange={field.onChange}
                      options={selectOptions('document_type')}
                      placeholder="—"
                    />
                  )}
                />
              )}
            </FormField>
            <FormField label="Número de documento" error={errors.document_number?.message}>
              {(p) => <Input {...p} inputMode="numeric" {...form.register('document_number')} />}
            </FormField>
          </div>

          {/* Nombres según tipo */}
          {personType === 'NATURAL' ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField label="Nombres" required error={errors.first_name?.message}>
                  {(p) => <Input {...p} {...form.register('first_name')} />}
                </FormField>
                <FormField label="Apellidos" required error={errors.last_name?.message}>
                  {(p) => <Input {...p} {...form.register('last_name')} />}
                </FormField>
              </div>
              <FormField label="Fecha de nacimiento" optional error={errors.birth_date?.message}>
                {(p) => <Input {...p} type="date" {...form.register('birth_date')} />}
              </FormField>
            </>
          ) : (
            <>
              <FormField label="Razón social" required error={errors.legal_name?.message}>
                {(p) => <Input {...p} {...form.register('legal_name')} />}
              </FormField>
              <FormField label="Nombre comercial" optional error={errors.trade_name?.message}>
                {(p) => <Input {...p} {...form.register('trade_name')} />}
              </FormField>
            </>
          )}

          {/* Contacto */}
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Correo" optional error={errors.email?.message}>
              {(p) => <Input {...p} type="email" inputMode="email" {...form.register('email')} />}
            </FormField>
            <FormField label="Teléfono" optional error={errors.phone?.message}>
              {(p) => <Input {...p} type="tel" inputMode="tel" {...form.register('phone')} />}
            </FormField>
            <FormField label="Teléfono alterno" optional error={errors.phone_alt?.message}>
              {(p) => <Input {...p} type="tel" inputMode="tel" {...form.register('phone_alt')} />}
            </FormField>
            <FormField label="WhatsApp" optional error={errors.whatsapp?.message}>
              {(p) => <Input {...p} type="tel" inputMode="tel" {...form.register('whatsapp')} />}
            </FormField>
          </div>

          <FormField label="Dirección" optional error={errors.address?.message}>
            {(p) => <Input {...p} {...form.register('address')} />}
          </FormField>

          {/* Contactos */}
          <div className="space-y-3 rounded-lg border border-zinc-200 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-zinc-700">Contactos</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => contacts.append({ full_name: '', position: '', area: '', email: '', phone: '', whatsapp: '', is_primary: false, notes: '' })}
              >
                Añadir contacto
              </Button>
            </div>
            {contacts.fields.length === 0 && (
              <p className="text-sm text-muted-foreground">Sin contactos adicionales.</p>
            )}
            {contacts.fields.map((field, index) => (
              <div key={field.id} className="space-y-2 rounded-md border border-zinc-100 bg-zinc-50/50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <FormField label="Nombre" required error={errors.contacts?.[index]?.full_name?.message}>
                    {(p) => <Input {...p} placeholder="Nombre completo" {...form.register(`contacts.${index}.full_name`)} />}
                  </FormField>
                  <Button type="button" variant="ghost" size="icon-sm" className="mt-5 shrink-0" onClick={() => contacts.remove(index)} aria-label="Eliminar contacto">
                    <Trash2 className="size-4" />
                  </Button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <FormField label="Cargo" optional>
                    {(p) => <Input {...p} placeholder="Cargo" {...form.register(`contacts.${index}.position`)} />}
                  </FormField>
                  <FormField label="Área" optional>
                    {(p) => <Input {...p} placeholder="Área" {...form.register(`contacts.${index}.area`)} />}
                  </FormField>
                  <FormField label="Correo" optional error={errors.contacts?.[index]?.email?.message}>
                    {(p) => <Input {...p} type="email" placeholder="Correo" {...form.register(`contacts.${index}.email`)} />}
                  </FormField>
                  <FormField label="Teléfono" optional>
                    {(p) => <Input {...p} type="tel" placeholder="Teléfono" {...form.register(`contacts.${index}.phone`)} />}
                  </FormField>
                </div>
                <label className="flex items-center gap-2 text-sm text-zinc-700">
                  <Controller
                    control={form.control}
                    name={`contacts.${index}.is_primary`}
                    render={({ field }) => <Checkbox checked={field.value} onCheckedChange={field.onChange} />}
                  />
                  Contacto principal
                </label>
              </div>
            ))}
          </div>

          {/* Catálogos */}
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Origen" optional error={errors.source_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="source_id"
                  render={({ field }) => (
                    <Select {...p} value={field.value} onValueChange={field.onChange} options={selectOptions('prospect_source')} placeholder="—" />
                  )}
                />
              )}
            </FormField>
            <FormField label="Canal de contacto inicial" optional error={errors.acquisition_channel_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="acquisition_channel_id"
                  render={({ field }) => (
                    <Select {...p} value={field.value} onValueChange={field.onChange} options={selectOptions('contact_channel')} placeholder="—" />
                  )}
                />
              )}
            </FormField>
            <FormField label="Nivel de interés" optional error={errors.interest_level_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="interest_level_id"
                  render={({ field }) => (
                    <Select {...p} value={field.value} onValueChange={field.onChange} options={selectOptions('interest_level')} placeholder="—" />
                  )}
                />
              )}
            </FormField>
            <FormField label="Prioridad" optional error={errors.priority_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="priority_id"
                  render={({ field }) => (
                    <Select {...p} value={field.value} onValueChange={field.onChange} options={selectOptions('priority')} placeholder="—" />
                  )}
                />
              )}
            </FormField>
          </div>

          {/* Responsable */}
          {canAssign && (
            <FormField label="Responsable" required={isNew} error={errors.owner_id?.message}>
              {(p) => (
                <Controller
                  control={form.control}
                  name="owner_id"
                  render={({ field }) => (
                    <Select
                      {...p}
                      value={field.value}
                      onValueChange={field.onChange}
                      options={(users.data ?? []).map((u) => ({ value: u.id, label: u.full_name }))}
                      placeholder="Selecciona un vendedor"
                    />
                  )}
                />
              )}
            </FormField>
          )}

          {/* Etiquetas */}
          <FormField label="Etiquetas" optional>
            {() => (
              <div className="grid max-h-40 gap-2 overflow-y-auto rounded-lg border border-zinc-200 p-2">
                {tags.data?.length ? (
                  tags.data.map((tag) => {
                    const selected = (form.watch('tags') ?? []).includes(tag.id)
                    return (
                      <label
                        key={tag.id}
                        className={cn(
                          'flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                          selected ? 'bg-zinc-50' : 'hover:bg-zinc-50',
                        )}
                      >
                        <Checkbox
                          checked={selected}
                          onCheckedChange={(v) => {
                            const current = form.getValues('tags') ?? []
                            form.setValue(
                              'tags',
                              v ? [...current, tag.id] : current.filter((id) => id !== tag.id),
                              { shouldValidate: true },
                            )
                          }}
                        />
                        <span className="text-zinc-800">{tag.name}</span>
                      </label>
                    )
                  })
                ) : (
                  <p className="px-2 py-1 text-sm text-muted-foreground">No hay etiquetas aún.</p>
                )}
              </div>
            )}
          </FormField>

          <FormField label="Notas" optional error={errors.notes?.message}>
            {(p) => <Textarea {...p} rows={3} {...form.register('notes')} />}
          </FormField>

          {/* Duplicados */}
          {duplicateResult && (
            <div
              className={cn(
                'rounded-lg border p-3 text-sm',
                isBlocked
                  ? 'border-red-200 bg-red-50 text-red-800'
                  : 'border-amber-200 bg-amber-50 text-amber-800',
              )}
            >
              <p className="flex items-center gap-2 font-medium">
                {isBlocked ? <Ban className="size-4" /> : <AlertTriangle className="size-4" />}
                {isBlocked ? 'No se puede guardar: posible duplicado' : 'Posible duplicado detectado'}
              </p>
              {duplicateResult.block_reason && <p className="mt-1">{duplicateResult.block_reason}</p>}
              {duplicateResult.matches.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {duplicateResult.matches.map((m) => (
                    <li key={m.prospect_id} className="flex items-center gap-2">
                      <CircleAlert className="size-3.5 opacity-70" />
                      <span>
                        {m.display_name} ({m.code}) — coincidencia por <strong>{m.field}</strong>
                      </span>
                      <Link
                        to={`/prospectos/${m.prospect_id}`}
                        className="text-brand-700 underline underline-offset-2 hover:text-brand-800"
                        onClick={onClose}
                      >
                        Ver ficha
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </form>
      </SheetContent>
    </Sheet>
  )
}
