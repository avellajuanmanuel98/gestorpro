import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

/**
 * Base de la API. Por defecto '/api' (mismo dominio: Django sirve la SPA, y en
 * desarrollo el proxy de Vite redirige /api → :8000). VITE_API_URL permite
 * apuntar a otro origen e INCLUYE el sufijo /api.
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_URL ?? '/api'

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export const tokenStorage = {
  get access() { return localStorage.getItem(ACCESS_KEY) },
  get refresh() { return localStorage.getItem(REFRESH_KEY) },
  set(tokens: { access: string; refresh?: string }) {
    localStorage.setItem(ACCESS_KEY, tokens.access)
    if (tokens.refresh) localStorage.setItem(REFRESH_KEY, tokens.refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/**
 * Refresh de un solo vuelo: los refresh tokens rotan y el anterior queda
 * revocado, así que si varias peticiones reciben 401 a la vez deben esperar
 * UNA sola renovación en lugar de lanzar varias (la segunda fallaría).
 */
let refreshInFlight: Promise<string> | null = null

export function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    const refresh = tokenStorage.refresh
    refreshInFlight = (refresh
      ? axios.post(`${API_BASE_URL}/auth/token/refresh/`, { refresh }).then(({ data }) => {
          tokenStorage.set({ access: data.access, refresh: data.refresh })
          return data.access as string
        })
      : Promise.reject(new Error('Sin sesión'))
    ).finally(() => { refreshInFlight = null })
  }
  return refreshInFlight
}

/** Se invoca cuando la sesión ya no puede renovarse. La registra el store de sesión. */
let onSessionExpired: () => void = () => {
  tokenStorage.clear()
  window.location.assign('/login')
}
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const isAuthCall = original?.url?.includes('/auth/login') || original?.url?.includes('/auth/token/refresh')
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true
      try {
        const access = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${access}`
        return apiClient(original)
      } catch {
        onSessionExpired()
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
