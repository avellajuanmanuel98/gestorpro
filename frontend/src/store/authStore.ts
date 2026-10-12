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
  /** Personal de la plataforma: entra a una empresa en modo soporte (solo lectura) y vuelve a la consola. */
  enterSupport: (access: string) => Promise<void>
  exitSupport: () => Promise<number | null>
}

// Mientras dura el soporte, los tokens propios del agente esperan aquí (solo en esta pestaña)
const STASH = 'gp_platform_tokens'
const stash = {
  save() { sessionStorage.setItem(STASH, JSON.stringify({ access: tokenStorage.access, refresh: tokenStorage.refresh })) },
  restore(): boolean {
    const raw = sessionStorage.getItem(STASH)
    if (!raw) return false
    sessionStorage.removeItem(STASH)
    const saved = JSON.parse(raw) as { access: string | null; refresh: string | null }
    tokenStorage.clear()
    if (saved.access) tokenStorage.set({ access: saved.access, refresh: saved.refresh ?? undefined })
    return Boolean(saved.access)
  },
  get active() { return sessionStorage.getItem(STASH) !== null },
}
export const supportStash = stash

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
        if (stash.active) await get().exitSupport() // primero se recupera la sesión propia, para revocarla
        try {
          await authApi.logout()
        } catch {
          // La sesión local se cierra igualmente
        }
        get().clear()
      },

      enterSupport: async (access) => {
        stash.save()
        tokenStorage.clear()
        tokenStorage.set({ access }) // sin refresh: el acceso vence con la sesión de soporte
        await get().refreshSession()
      },

      exitSupport: async () => {
        const tenantId = get().session?.tenant?.id ?? null
        try {
          await authApi.endSupport()
        } catch {
          // Si ya venció, igual se vuelve a la consola
        }
        stash.restore()
        await get().refreshSession()
        return tenantId
      },

      clear: () => {
        sessionStorage.removeItem(STASH)
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
  // Venció una sesión de soporte: se vuelve a la consola con los tokens propios del agente
  if (stash.active && stash.restore()) {
    window.location.assign('/platform')
    return
  }
  useAuthStore.getState().clear()
  if (window.location.pathname !== '/login') window.location.assign('/login')
})

/** Permisos solo para adaptar la interfaz; la autorización real está en el backend. */
export function useCan() {
  const permissions = useAuthStore((s) => s.session?.permissions)
  return (permission: string) => Boolean(permissions?.includes(permission))
}

/** Funcionalidades del plan, solo para adaptar la interfaz (el backend las exige). */
export function useHasFeature() {
  const features = useAuthStore((s) => s.session?.features)
  return (feature: string) => Boolean(features?.includes(feature))
}

/** Módulos opcionales de la empresa (producción, mermas), solo para adaptar la UI (el backend los exige). */
export function useHasModule() {
  const modules = useAuthStore((s) => s.session?.tenant?.modules)
  return (module: string) => Boolean(modules?.includes(module))
}
