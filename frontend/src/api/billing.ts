import apiClient from './client'
import type { Invoice, InvoiceInput, BillingSummary, PaginatedResponse } from '@/types'

export const billingApi = {
  list: async (params?: { status?: string; invoice_type?: string; search?: string; page?: number; page_size?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Invoice>>('/billing/invoices/', { params })
    return data
  },

  get: async (id: number): Promise<Invoice> => {
    const { data } = await apiClient.get<Invoice>(`/billing/invoices/${id}/`)
    return data
  },

  create: async (payload: InvoiceInput): Promise<Invoice> => {
    const { data } = await apiClient.post<Invoice>('/billing/invoices/', payload)
    return data
  },

  update: async (id: number, payload: Partial<InvoiceInput>): Promise<Invoice> => {
    const { data } = await apiClient.patch<Invoice>(`/billing/invoices/${id}/`, payload)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/billing/invoices/${id}/`)
  },

  summary: async (): Promise<BillingSummary> => {
    const { data } = await apiClient.get<BillingSummary>('/billing/summary/')
    return data
  },

  monthlyRevenue: async (): Promise<{ month: string; mes: string; total: string }[]> => {
    const { data } = await apiClient.get('/billing/monthly-revenue/')
    return data
  },

  recent: async (): Promise<{
    id: number; number: string; customer: string; total: string; status: Invoice['status']
  }[]> => {
    const { data } = await apiClient.get('/billing/recent/')
    return data
  },
}
