import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/shared/api/errors'
import { P, usePermissions } from '@/shared/auth/permissions'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { type User, type UserStatusFilter, usersKeys, usersService } from '../api/users-service'

export function useUsersViewModel() {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<UserStatusFilter>('active')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<User | 'new' | null>(null)
  const [confirming, setConfirming] = useState<User | null>(null)
  const q = useDebounce(search)

  const filters = { q, status, page }
  const query = useQuery({ queryKey: usersKeys.list(filters), queryFn: () => usersService.list(filters), placeholderData: keepPreviousData })

  const invalidate = () => qc.invalidateQueries({ queryKey: usersKeys.all })

  const toggleActive = useMutation({
    mutationFn: (u: User) => (u.is_active ? usersService.deactivate(u.id) : usersService.activate(u.id)),
    onSuccess: (u) => {
      toast.success(u.is_active ? `${u.full_name} fue reactivado` : `${u.full_name} fue desactivado`)
      invalidate()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return {
    canManage: can(P.USERS_MANAGE),
    search,
    setSearch: (v: string) => {
      setSearch(v)
      setPage(1)
    },
    status,
    setStatus: (v: UserStatusFilter) => {
      setStatus(v)
      setPage(1)
    },
    page,
    setPage,
    query,
    clearFilters: () => {
      setSearch('')
      setStatus('all')
      setPage(1)
    },
    editing,
    openCreate: () => setEditing('new'),
    openEdit: (u: User) => setEditing(u),
    closeEditor: () => setEditing(null),
    onSaved: invalidate,
    confirming,
    askToggle: (u: User) => (u.is_active ? setConfirming(u) : toggleActive.mutate(u)),
    closeConfirm: () => setConfirming(null),
    confirmToggle: () => (confirming ? toggleActive.mutateAsync(confirming) : Promise.resolve()),
  }
}
