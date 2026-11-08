import { api, type Schemas, unwrap } from '@/shared/api/client'

export type Interaction = Schemas['InteractionRead']
export type InteractionCreate = Schemas['InteractionCreate']
export type InteractionUpdate = Schemas['InteractionUpdate']

export const interactionsKeys = {
  all: ['interactions'] as const,
  list: (prospectId: string) => ['interactions', 'list', prospectId] as const,
}

export const interactionsService = {
  list: (prospectId: string) =>
    unwrap(
      api.GET('/api/v1/prospects/{prospect_id}/interactions', {
        params: { path: { prospect_id: prospectId }, query: { page: 1, page_size: 100 } },
      }),
    ),
  create: (prospectId: string, body: InteractionCreate) =>
    unwrap(
      api.POST('/api/v1/prospects/{prospect_id}/interactions', {
        params: { path: { prospect_id: prospectId } },
        body,
      }),
    ),
  update: (prospectId: string, interactionId: string, body: InteractionUpdate) =>
    unwrap(
      api.PATCH('/api/v1/prospects/{prospect_id}/interactions/{interaction_id}', {
        params: { path: { prospect_id: prospectId, interaction_id: interactionId } },
        body,
      }),
    ),
  delete: (prospectId: string, interactionId: string) =>
    unwrap(
      api.DELETE('/api/v1/prospects/{prospect_id}/interactions/{interaction_id}', {
        params: { path: { prospect_id: prospectId, interaction_id: interactionId } },
      }),
    ),
}
