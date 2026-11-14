import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { type Schemas } from '@/shared/api/client'
import { errorMessage } from '@/shared/api/errors'
import { useDebounce } from '@/shared/hooks/use-debounce'

import { prospectsKeys, prospectsService, type ProspectFilters } from '../api/prospects-service'

const STATUS_VALUES = ['ACTIVO', 'INACTIVO', 'CONVERTIDO', 'PERDIDO'] as const
const PERSON_TYPES = ['NATURAL', 'JURIDICA'] as const
const RELATIONSHIP_TYPES = ['PROSPECTO', 'CLIENTE'] as const

function filtersFromParams(sp: URLSearchParams): ProspectFilters {
  const status = sp.get('status')
  const page = Number(sp.get('page') ?? '1')
  return {
    page: Number.isNaN(page) || page < 1 ? 1 : page,
    status: STATUS_VALUES.includes(status as any) ? (status as ProspectFilters['status']) : 'ACTIVO',
    q: sp.get('q') || undefined,
    person_type: PERSON_TYPES.includes(sp.get('person_type') as any) ? (sp.get('person_type') as ProspectFilters['person_type']) : undefined,
    relationship_type: RELATIONSHIP_TYPES.includes(sp.get('relationship_type') as any) ? (sp.get('relationship_type') as ProspectFilters['relationship_type']) : undefined,
    owner_id: sp.get('owner_id') || undefined,
    interest_level_id: sp.get('interest_level_id') || undefined,
    interest_level_code: sp.get('interest_level_code') || undefined,
    priority_id: sp.get('priority_id') || undefined,
    source_id: sp.get('source_id') || undefined,
    without_contact_days: parseIntParam(sp.get('without_contact_days')),
    next_action_today: sp.get('next_action_today') === 'true' ? true : undefined,
    created_since_days: parseIntParam(sp.get('created_since_days')),
  }
}

function parseIntParam(value: string | null): number | undefined {
  if (!value) return undefined
  const n = Number(value)
  return Number.isNaN(n) ? undefined : n
}

function paramsFromFilters(filters: ProspectFilters, search: string): URLSearchParams {
  const sp = new URLSearchParams()
  if (filters.status && filters.status !== 'ACTIVO') sp.set('status', filters.status)
  if (filters.page > 1) sp.set('page', String(filters.page))
  if (search) sp.set('q', search)
  if (filters.person_type) sp.set('person_type', filters.person_type)
  if (filters.relationship_type) sp.set('relationship_type', filters.relationship_type)
  if (filters.owner_id) sp.set('owner_id', filters.owner_id)
  if (filters.interest_level_id) sp.set('interest_level_id', filters.interest_level_id)
  if (filters.interest_level_code) sp.set('interest_level_code', filters.interest_level_code)
  if (filters.priority_id) sp.set('priority_id', filters.priority_id)
  if (filters.source_id) sp.set('source_id', filters.source_id)
  if (filters.without_contact_days) sp.set('without_contact_days', String(filters.without_contact_days))
  if (filters.next_action_today) sp.set('next_action_today', 'true')
  if (filters.created_since_days) sp.set('created_since_days', String(filters.created_since_days))
  return sp
}

export function useProspectsViewModel() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialFilters = filtersFromParams(searchParams)
  const [filters, setFiltersState] = useState<ProspectFilters>(initialFilters)
  const [search, setSearchState] = useState(searchParams.get('q') ?? '')
  const debouncedSearch = useDebounce(search, 300)
  const queryClient = useQueryClient()

  const setFilters = (updater: ProspectFilters | ((prev: ProspectFilters) => ProspectFilters)) => {
    setFiltersState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      setSearchParams(paramsFromFilters(next, search))
      return next
    })
  }

  const setSearch = (value: string) => {
    setSearchState(value)
    setFiltersState((prev) => {
      const next = { ...prev, page: 1 }
      setSearchParams(paramsFromFilters(next, value))
      return next
    })
  }

  const currentFilters: ProspectFilters = {
    ...filters,
    q: debouncedSearch || undefined,
    page: filters.page,
  }

  const { data, isLoading } = useQuery({
    queryKey: prospectsKeys.list(currentFilters),
    queryFn: () => prospectsService.list(currentFilters),
    placeholderData: keepPreviousData,
  })

  const deleteMutation = useMutation({
    mutationFn: prospectsService.delete,
    onSuccess: () => {
      toast.success('Prospecto eliminado')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const assignMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Schemas['AssignRequest']) => prospectsService.assign(id, body),
    onSuccess: () => {
      toast.success('Prospecto asignado')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const changeStatusMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Schemas['StatusChangeRequest']) => prospectsService.changeStatus(id, body),
    onSuccess: () => {
      toast.success('Estado actualizado')
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const bulkAssignMutation = useMutation({
    mutationFn: prospectsService.bulkAssign,
    onSuccess: (_, vars) => {
      toast.success(`${vars.prospect_ids.length} prospecto(s) asignado(s)`)
      queryClient.invalidateQueries({ queryKey: prospectsKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return {
    prospects: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? 1,
    pageSize: data?.page_size ?? 25,
    isLoading,
    search,
    setSearch,
    filters,
    setFilters,
    deleteProspect: deleteMutation.mutate,
    deletePending: deleteMutation.isPending,
    assign: assignMutation.mutate,
    assignPending: assignMutation.isPending,
    changeStatus: changeStatusMutation.mutate,
    changeStatusPending: changeStatusMutation.isPending,
    bulkAssign: bulkAssignMutation.mutate,
    bulkAssignPending: bulkAssignMutation.isPending,
  }
}
