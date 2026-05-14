import apiClient from './client'
import type { Product, Category, PaginatedResponse } from '@/types'

export const inventoryApi = {
  // ── Productos ──────────────────────────────────────────────────────────────
  listProducts: async (params?: { search?: string; category?: number; product_type?: string; is_active?: boolean }) => {
    const { data } = await apiClient.get<PaginatedResponse<Product>>('/inventory/products/', { params })
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

  deleteProduct: async (id: number): Promise<void> => {
    await apiClient.delete(`/inventory/products/${id}/`)
  },

  // ── Categorías ─────────────────────────────────────────────────────────────
  listCategories: async () => {
    const { data } = await apiClient.get<PaginatedResponse<Category>>('/inventory/categories/')
    return data
  },

  createCategory: async (payload: Partial<Category>): Promise<Category> => {
    const { data } = await apiClient.post<Category>('/inventory/categories/', payload)
    return data
  },

  updateCategory: async (id: number, payload: Partial<Category>): Promise<Category> => {
    const { data } = await apiClient.put<Category>(`/inventory/categories/${id}/`, payload)
    return data
  },

  deleteCategory: async (id: number): Promise<void> => {
    await apiClient.delete(`/inventory/categories/${id}/`)
  },
}
