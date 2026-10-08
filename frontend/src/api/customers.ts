import apiClient from './client'
import type { Customer, PaginatedResponse } from '@/types'

export const customersApi = {
  list: async (params?: { search?: string; status?: string; page?: number; page_size?: number }) =>
    (await apiClient.get<PaginatedResponse<Customer>>('/customers/', { params })).data,

  get: async (id: number): Promise<Customer> => (await apiClient.get<Customer>(`/customers/${id}/`)).data,

  create: async (payload: Partial<Customer>): Promise<Customer> =>
    (await apiClient.post<Customer>('/customers/', payload)).data,

  update: async (id: number, payload: Partial<Customer>): Promise<Customer> =>
    (await apiClient.put<Customer>(`/customers/${id}/`, payload)).data,

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/customers/${id}/`)
  },
}
