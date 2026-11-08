import { api, refreshSession, type Schemas, unwrap } from '@/shared/api/client'
import { queryClient } from '@/shared/api/query-client'
import { useSessionStore } from '@/shared/auth/session-store'

export const authService = {
  async login(email: string, password: string) {
    const session = await unwrap(api.POST('/api/v1/auth/login', { body: { email, password } }))
    useSessionStore.getState().setSession(session.access_token, session.user)
    return session
  },

  async logout() {
    try {
      await api.POST('/api/v1/auth/logout')
    } finally {
      useSessionStore.getState().clear('logout')
      queryClient.clear() // no dejar datos de esta sesión en memoria
    }
  },

  /** Al abrir la app: si la cookie de refresh sigue vigente, se recupera la sesión sin pedir clave. */
  async bootstrap() {
    const ok = await refreshSession()
    if (!ok) useSessionStore.getState().clear()
  },

  async changePassword(body: Schemas['ChangePasswordRequest']) {
    await unwrap(api.POST('/api/v1/auth/change-password', { body }))
    const me = await unwrap(api.GET('/api/v1/auth/me'))
    useSessionStore.getState().setUser(me)
  },
}
