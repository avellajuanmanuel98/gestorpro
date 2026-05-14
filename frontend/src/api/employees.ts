import apiClient from './client'
import type { Employee, PaginatedResponse } from '@/types'

export const employeesApi = {
  list: async (params?: { search?: string; status?: string; department?: string; page?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Employee>>('/employees/', { params })
    return data
  },

  get: async (id: number): Promise<Employee> => {
    const { data } = await apiClient.get<Employee>(`/employees/${id}/`)
    return data
  },

  create: async (payload: Partial<Employee>): Promise<Employee> => {
    const { data } = await apiClient.post<Employee>('/employees/', payload)
    return data
  },

  update: async (id: number, payload: Partial<Employee>): Promise<Employee> => {
    const { data } = await apiClient.put<Employee>(`/employees/${id}/`, payload)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/employees/${id}/`)
  },
}
