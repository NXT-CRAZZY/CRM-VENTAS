import createClient from 'openapi-fetch'
import { useSessionStore } from '@/shared/auth/session-store'
import { ApiError } from './errors'
import type { components, paths } from './schema'

export type Schemas = components['schemas']

const AUTH_PATHS = ['/api/v1/auth/login', '/api/v1/auth/refresh', '/api/v1/auth/logout']

let refreshing: Promise<boolean> | null = null

/** Renueva el access token usando la cookie httpOnly. Una sola petición aunque fallen varias a la vez. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= (async () => {
    try {
      const res = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'same-origin' })
      if (!res.ok) return false
      const body = (await res.json()) as Schemas['TokenResponse']
      useSessionStore.getState().setSession(body.access_token, body.user)
      return true
    } catch {
      return false
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

async function authFetch(request: Request): Promise<Response> {
  const retry = request.clone()
  const withToken = (req: Request) => {
    const token = useSessionStore.getState().accessToken
    if (token) req.headers.set('Authorization', `Bearer ${token}`)
    return req
  }

  let response = await fetch(withToken(request))
  const isAuthCall = AUTH_PATHS.some((p) => new URL(request.url).pathname.startsWith(p))
  if (response.status === 401 && !isAuthCall) {
    if (await refreshSession()) {
      response = await fetch(withToken(retry))
    } else {
      useSessionStore.getState().clear('expired')
    }
  }
  return response
}

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  credentials: 'same-origin',
  fetch: (input) => authFetch(input as Request).catch(() => new Response(null, { status: 0 } as ResponseInit)),
})

/** Convierte la respuesta de openapi-fetch en datos o lanza ApiError (para TanStack Query). */
export async function unwrap<T>(promise: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await promise
  if (error !== undefined || !response.ok) throw new ApiError(response.status, error)
  return data as T
}
