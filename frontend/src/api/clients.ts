import apiClient from './client'
import type { Client, PaginatedResponse } from '@/types'

export const clientsApi = {
  list: async (params?: { search?: string; status?: string; page?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Client>>('/clients/', { params })
    return data
  },

  get: async (id: number): Promise<Client> => {
    const { data } = await apiClient.get<Client>(`/clients/${id}/`)
    return data
  },

  create: async (payload: Partial<Client>): Promise<Client> => {
    const { data } = await apiClient.post<Client>('/clients/', payload)
    return data
  },

  update: async (id: number, payload: Partial<Client>): Promise<Client> => {
    const { data } = await apiClient.put<Client>(`/clients/${id}/`, payload)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/clients/${id}/`)
  },
}
