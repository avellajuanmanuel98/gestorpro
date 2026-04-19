import apiClient from './client'
import type { AuthTokens, User } from '@/types'

export const authApi = {
  login: async (email: string, password: string): Promise<AuthTokens> => {
    const { data } = await apiClient.post<AuthTokens>('/auth/login/', { email, password })
    return data
  },

  register: async (payload: {
    email: string
    first_name: string
    last_name: string
    password: string
    password2: string
  }) => {
    const { data } = await apiClient.post('/auth/register/', payload)
    return data
  },

  getProfile: async (): Promise<User> => {
    const { data } = await apiClient.get<User>('/auth/profile/')
    return data
  },

  updateProfile: async (payload: Partial<User>): Promise<User> => {
    const { data } = await apiClient.put<User>('/auth/profile/', payload)
    return data
  },
}
