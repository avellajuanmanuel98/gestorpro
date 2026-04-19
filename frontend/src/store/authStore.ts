import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'

// Zustand es como useState pero global — cualquier componente
// puede leer o modificar este estado sin pasar props

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  // persist guarda el estado en localStorage automáticamente
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setUser: (user) => set({ user, isAuthenticated: true }),

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, isAuthenticated: false })
      },
    }),
    { name: 'auth-store' }
  )
)
