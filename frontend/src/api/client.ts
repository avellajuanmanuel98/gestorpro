import axios from 'axios'

// En desarrollo, el proxy de Vite redirige /api/* → http://127.0.0.1:8000/api/*
// En producción, VITE_API_URL apunta a la URL del backend en Railway
const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// INTERCEPTOR DE REQUEST
// Antes de cada petición, agrega el token JWT automáticamente
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// INTERCEPTOR DE RESPONSE
// Si el backend devuelve 401 (token expirado), renueva el token
// y reintenta la petición original sin que el usuario note nada
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')

      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/token/refresh/`, { refresh })
          localStorage.setItem('access_token', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return apiClient(original)
        } catch {
          // Si el refresh también falló, cerramos sesión
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
