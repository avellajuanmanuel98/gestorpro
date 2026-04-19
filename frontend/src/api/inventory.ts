import apiClient from './client'
import type { Product, Category, PaginatedResponse } from '@/types'

export const inventoryApi = {
  listProducts: async (params?: { search?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get<PaginatedResponse<Product>>('/inventory/products/', { params })
    return data
  },

  listCategories: async () => {
    const { data } = await apiClient.get<PaginatedResponse<Category>>('/inventory/categories/')
    return data
  },

  createProduct: async (payload: Partial<Product>): Promise<Product> => {
    const { data } = await apiClient.post<Product>('/inventory/products/', payload)
    return data
  },

  updateProduct: async (id: number, payload: Partial<Product>): Promise<Product> => {
    const { data } = await apiClient.put<Product>(`/inventory/products/${id}/`, payload)
    return data
  },
}
