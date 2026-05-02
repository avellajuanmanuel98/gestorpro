import apiClient from './client'
import type { Invoice, BillingSummary, PaginatedResponse } from '@/types'

export const billingApi = {
  list: async (params?: { status?: string; invoice_type?: string; page?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Invoice>>('/billing/invoices/', { params })
    return data
  },

  get: async (id: number): Promise<Invoice> => {
    const { data } = await apiClient.get<Invoice>(`/billing/invoices/${id}/`)
    return data
  },

  create: async (payload: Partial<Invoice>): Promise<Invoice> => {
    const { data } = await apiClient.post<Invoice>('/billing/invoices/', payload)
    return data
  },

  update: async (id: number, payload: Partial<Invoice>): Promise<Invoice> => {
    const { data } = await apiClient.put<Invoice>(`/billing/invoices/${id}/`, payload)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/billing/invoices/${id}/`)
  },

  summary: async (): Promise<BillingSummary> => {
    const { data } = await apiClient.get<BillingSummary>('/billing/summary/')
    return data
  },

  monthlyRevenue: async (): Promise<{ mes: string; total: number }[]> => {
    const { data } = await apiClient.get('/billing/monthly-revenue/')
    return data
  },

  recent: async (): Promise<{
    id: number; number: string; client: string; total: number; status: string
  }[]> => {
    const { data } = await apiClient.get('/billing/recent/')
    return data
  },
}
