import apiClient from './client'
import type { Supplier, PaginatedResponse } from '@/types'

export const suppliersApi = {
  list: async (params?: { search?: string; status?: string; category?: string; page?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Supplier>>('/suppliers/', { params })
    return data
  },

  get: async (id: number): Promise<Supplier> => {
    const { data } = await apiClient.get<Supplier>(`/suppliers/${id}/`)
    return data
  },

  create: async (payload: Partial<Supplier>): Promise<Supplier> => {
    const { data } = await apiClient.post<Supplier>('/suppliers/', payload)
    return data
  },

  update: async (id: number, payload: Partial<Supplier>): Promise<Supplier> => {
    const { data } = await apiClient.put<Supplier>(`/suppliers/${id}/`, payload)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/suppliers/${id}/`)
  },
}
