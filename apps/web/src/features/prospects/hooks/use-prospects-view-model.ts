import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { type Schemas } from '@/shared/api/client'
import { errorMessage } from '@/shared/api/errors'
import { useDebounce } from '@/shared/hooks/use-debounce'

import { prospectsKeys, prospectsService, type ProspectFilters } from '../api/prospects-service'

export function useProspectsViewModel() {
  const [filters, setFilters] = useState<ProspectFilters>({ page: 1, status: 'ACTIVO' })
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 300)
  const queryClient = useQueryClient()

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
