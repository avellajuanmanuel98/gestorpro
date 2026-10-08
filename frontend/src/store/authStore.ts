import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi } from '@/api/auth'
import { setSessionExpiredHandler, tokenStorage } from '@/api/client'
import type { AuthTokens, Session, User } from '@/types'

interface AuthState {
  session: Session | null
  user: User | null
  isAuthenticated: boolean
  /** Guarda tokens y carga la sesión (usuario, empresa activa, rol, permisos). */
  startSession: (tokens: AuthTokens) => Promise<Session>
  refreshSession: () => Promise<void>
  switchTenant: (tenantId: number) => Promise<void>
  logout: () => Promise<void>
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      session: null,
      user: null,
      isAuthenticated: false,

      startSession: async (tokens) => {
        tokenStorage.set(tokens)
        const session = await authApi.me()
        set({ session, user: session.user, isAuthenticated: true })
        return session
      },

      refreshSession: async () => {
        const session = await authApi.me()
        set({ session, user: session.user, isAuthenticated: true })
      },

      switchTenant: async (tenantId) => {
        const tokens = await authApi.switchTenant(tenantId)
        await get().startSession(tokens)
      },

      logout: async () => {
        try {
          await authApi.logout()
        } catch {
          // La sesión local se cierra igualmente
        }
        get().clear()
      },

      clear: () => {
        tokenStorage.clear()
        set({ session: null, user: null, isAuthenticated: false })
      },
    }),
    {
      name: 'auth-store',
      partialize: (s) => ({ session: s.session, user: s.user, isAuthenticated: s.isAuthenticated }),
    },
  ),
)

setSessionExpiredHandler(() => {
  useAuthStore.getState().clear()
  if (window.location.pathname !== '/login') window.location.assign('/login')
})

/** Permisos solo para adaptar la interfaz; la autorización real está en el backend. */
export function useCan() {
  const permissions = useAuthStore((s) => s.session?.permissions)
  return (permission: string) => Boolean(permissions?.includes(permission))
}
