import { useQuery } from '@tanstack/react-query'
import { api, type Schemas, unwrap } from './client'

export type CatalogCode =
  | 'document_type'
  | 'contact_channel'
  | 'contact_mode'
  | 'contact_result'
  | 'interest_level'
  | 'opportunity_type'
  | 'prospect_source'
  | 'priority'
  | 'loss_reason'
  | 'discard_reason'
  | 'task_type'
  | 'pipeline_stage'

/**
 * Opciones activas de catálogos para formularios y badges. Nada de valores de negocio
 * hardcodeados en el frontend: todo sale de aquí.
 */
export function useCatalogBundle(codes: CatalogCode[]) {
  const key = [...codes].sort().join(',')
  return useQuery({
    queryKey: ['catalogs', 'bundle', key],
    queryFn: () => unwrap(api.GET('/api/v1/catalogs/bundle', { params: { query: { codes: key } } })),
    select: (d) => d.catalogs as Partial<Record<CatalogCode, Schemas['CatalogOptionRead'][]>>,
    staleTime: 5 * 60_000,
  })
}
