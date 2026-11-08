import { MoreHorizontal, Pencil, RefreshCcw, Trash2, UserCog } from 'lucide-react'
import { P, usePermissions } from '@/shared/auth/permissions'
import { Button } from '@/shared/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/ui/menus'
import type { Prospect } from '../api/prospects-service'

export interface ProspectActionsMenuProps {
  prospect: Prospect
  onEdit?: () => void
  onAssign?: () => void
  onChangeStatus?: () => void
  onDelete?: () => void
  label?: string
}

export function ProspectActionsMenu({
  prospect,
  onEdit,
  onAssign,
  onChangeStatus,
  onDelete,
  label = 'Acciones',
}: ProspectActionsMenuProps) {
  const { can, canAny } = usePermissions()
  const canUpdate = can(P.PROSPECTS_UPDATE_OWN) || can(P.PROSPECTS_UPDATE_ALL)
  const canAssign = can(P.PROSPECTS_ASSIGN)
  const canDelete = can(P.PROSPECTS_DELETE)

  if (!canAny(P.PROSPECTS_UPDATE_OWN, P.PROSPECTS_UPDATE_ALL, P.PROSPECTS_ASSIGN, P.PROSPECTS_DELETE)) {
    return null
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
        <Button variant="ghost" size="icon-sm" aria-label={`${label} de ${prospect.display_name}`}>
          <MoreHorizontal />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        {onEdit && canUpdate && (
          <DropdownMenuItem onSelect={onEdit}>
            <Pencil /> Editar
          </DropdownMenuItem>
        )}
        {onAssign && canAssign && (
          <DropdownMenuItem onSelect={onAssign}>
            <UserCog /> Asignar
          </DropdownMenuItem>
        )}
        {onChangeStatus && canUpdate && (
          <DropdownMenuItem onSelect={onChangeStatus}>
            <RefreshCcw /> Cambiar estado
          </DropdownMenuItem>
        )}
        {onDelete && canDelete && (
          <DropdownMenuItem destructive onSelect={onDelete}>
            <Trash2 /> Eliminar
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
