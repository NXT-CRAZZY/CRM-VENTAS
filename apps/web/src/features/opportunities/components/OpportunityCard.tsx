import { Calendar, DollarSign, MoreHorizontal, Trash2, User } from 'lucide-react'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/ui/menus'

import { type Opportunity } from '../api/opportunities-service'

export function OpportunityCard({
  opportunity,
  onEdit,
  onDelete,
}: {
  opportunity: Opportunity
  onEdit: (o: Opportunity) => void
  onDelete: (o: Opportunity) => void
}) {
  return (
    <Card className="group cursor-grab p-3 active:cursor-grabbing">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-zinc-900">{opportunity.title}</p>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" className="-mr-1 -mt-1 opacity-0 group-hover:opacity-100">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => onEdit(opportunity)}>Editar</DropdownMenuItem>
            <DropdownMenuItem destructive onSelect={() => onDelete(opportunity)}>
              <Trash2 className="size-4" /> Eliminar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {opportunity.prospect && (
        <p className="mt-1 text-xs text-zinc-500">{opportunity.prospect.display_name}</p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <Badge tone={opportunity.client_status === 'EXISTENTE' ? 'info' : 'neutral'}>{opportunity.client_status === 'EXISTENTE' ? 'Existente' : 'Nuevo'}</Badge>
        {opportunity.type && <Badge tone="neutral">{opportunity.type.name}</Badge>}
        {opportunity.probability !== null && opportunity.probability !== undefined && (
          <Badge tone="brand">{opportunity.probability}%</Badge>
        )}
      </div>

      <div className="mt-2.5 space-y-1 text-xs text-muted-foreground">
        {opportunity.estimated_amount !== null && opportunity.estimated_amount !== undefined && (
          <div className="flex items-center gap-1">
            <DollarSign className="size-3.5" />
            {formatMoney(Number(opportunity.estimated_amount))}
          </div>
        )}
        {opportunity.expected_close_date && (
          <div className="flex items-center gap-1">
            <Calendar className="size-3.5" />
            {formatDate(opportunity.expected_close_date)}
          </div>
        )}
        {opportunity.owner && (
          <div className="flex items-center gap-1">
            <User className="size-3.5" />
            {opportunity.owner.full_name}
          </div>
        )}
      </div>
    </Card>
  )
}
