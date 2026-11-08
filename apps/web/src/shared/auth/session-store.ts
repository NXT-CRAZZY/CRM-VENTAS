import { create } from 'zustand'
import type { components } from '@/shared/api/schema'

export type SessionUser = components['schemas']['SessionUser']
type Status = 'loading' | 'authenticated' | 'anonymous'

interface SessionState {
  status: Status
  /** El access token vive solo en memoria; el refresh token está en una cookie httpOnly. */
  accessToken: string | null
  user: SessionUser | null
  /** Motivo del cierre, para mostrar un aviso amable en el login. */
  endedReason: 'expired' | 'logout' | null
  setSession: (token: string, user: SessionUser) => void
  setUser: (user: SessionUser) => void
  clear: (reason?: 'expired' | 'logout') => void
}

export const useSessionStore = create<SessionState>((set) => ({
  status: 'loading',
  accessToken: null,
  user: null,
  endedReason: null,
  setSession: (accessToken, user) => set({ accessToken, user, status: 'authenticated', endedReason: null }),
  setUser: (user) => set({ user }),
  clear: (reason) => set({ accessToken: null, user: null, status: 'anonymous', endedReason: reason ?? null }),
}))
