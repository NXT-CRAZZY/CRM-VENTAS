import { useDraggable, useDroppable, DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { useCatalogBundle } from '@/shared/api/catalogs'
import { errorMessage } from '@/shared/api/errors'
import { formatMoney } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { EmptyState } from '@/shared/ui/feedback'
import { ConfirmDialog } from '@/shared/ui/misc'
import { PageContainer, PageHeader } from '@/shared/ui/page'

import { opportunitiesKeys, opportunitiesService, type Opportunity } from '../api/opportunities-service'
import { OpportunityCard } from '../components/OpportunityCard'
import { OpportunityFormSheet } from '../components/OpportunityFormSheet'

function DraggableOpportunityCard({
  opportunity,
  onEdit,
  onDelete,
}: {
  opportunity: Opportunity
  onEdit: (o: Opportunity) => void
  onDelete: (o: Opportunity) => void
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: opportunity.id,
    data: { opportunity },
  })

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={cn('transition-opacity', isDragging && 'opacity-40')}
    >
      <OpportunityCard opportunity={opportunity} onEdit={onEdit} onDelete={onDelete} />
    </div>
  )
}

function StageColumn({
  stage,
  opportunities,
  onEdit,
  onDelete,
}: {
  stage: { id: string; name: string; color?: string | null }
  opportunities: Opportunity[]
  onEdit: (o: Opportunity) => void
  onDelete: (o: Opportunity) => void
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage.id,
    data: { stage },
  })
  const total = opportunities.reduce((sum, o) => sum + (Number(o.estimated_amount) || 0), 0)

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex min-w-[260px] flex-1 flex-col rounded-lg p-3 transition-colors',
        isOver ? 'bg-zinc-100' : 'bg-zinc-50/70',
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="size-2.5 rounded-full"
            style={{ backgroundColor: stage.color ?? '#71717A' }}
          />
          <h2 className="text-sm font-semibold text-zinc-900">{stage.name}</h2>
        </div>
        <Badge tone="neutral">{opportunities.length}</Badge>
      </div>

      <div className="flex-1 space-y-3">
        {opportunities.map((o) => (
          <DraggableOpportunityCard key={o.id} opportunity={o} onEdit={onEdit} onDelete={onDelete} />
        ))}
      </div>

      {total > 0 && (
        <div className="mt-3 border-t border-zinc-200 pt-2 text-xs font-medium text-zinc-700">
          Total estimado: {formatMoney(total)}
        </div>
      )}
    </div>
  )
}

export default function PipelinePage() {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState<Opportunity | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Opportunity | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    }),
  )

  const stagesQ = useCatalogBundle(['pipeline_stage'])
  const listQ = useQuery({
    queryKey: opportunitiesKeys.list({}),
    queryFn: () => opportunitiesService.list({}),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, stage_id }: { id: string; stage_id: string }) =>
      opportunitiesService.update(id, { stage_id }),
    onSuccess: () => {
      toast.success('Oportunidad movida')
      queryClient.invalidateQueries({ queryKey: opportunitiesKeys.all })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: (o: Opportunity) => opportunitiesService.delete(o.id),
    onSuccess: () => {
      toast.success('Oportunidad eliminada')
      queryClient.invalidateQueries({ queryKey: opportunitiesKeys.all })
      setDeleting(null)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const opportunities = listQ.data?.items ?? []
  const stages = stagesQ.data?.pipeline_stage ?? []

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over) return
    const opportunityId = active.id as string
    const newStageId = over.id as string
    const currentStageId = (active.data.current as { opportunity: Opportunity } | undefined)?.opportunity?.stage?.id
    if (currentStageId === newStageId) return
    updateMutation.mutate({ id: opportunityId, stage_id: newStageId })
  }

  return (
    <PageContainer>
      <PageHeader
        title="Pipeline de ventas"
        description="Arrastra las oportunidades entre etapas para actualizar el pipeline."
        actions={
          <Button onClick={() => setFormOpen('new')}>
            <Plus className="size-4" />
            Nueva oportunidad
          </Button>
        }
      />

      {stages.length === 0 ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="No hay etapas configuradas"
          description="El catálogo de etapas del pipeline no está disponible."
        />
      ) : (
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {stages.map((stage) => (
              <StageColumn
                key={stage.id}
                stage={stage}
                opportunities={opportunities.filter((o) => o.stage.id === stage.id)}
                onEdit={setFormOpen}
                onDelete={setDeleting}
              />
            ))}
          </div>
        </DndContext>
      )}

      {formOpen && formOpen !== 'new' && (
        <OpportunityFormSheet
          prospectId={formOpen.prospect.id}
          opportunity={formOpen}
          onClose={() => setFormOpen(null)}
        />
      )}
      {formOpen === 'new' && (
        <OpportunityFormSheet prospectId="" opportunity="new" onClose={() => setFormOpen(null)} />
      )}

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="¿Eliminar oportunidad?"
        description={`Se eliminará "${deleting?.title}". Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={async () => {
          if (deleting) await deleteMutation.mutateAsync(deleting)
        }}
      />
    </PageContainer>
  )
}
