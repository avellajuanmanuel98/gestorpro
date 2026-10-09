import apiClient from './client'
import type { Product, Category, PaginatedResponse } from '@/types'

export const inventoryApi = {
  // ── Productos ──────────────────────────────────────────────────────────────
  listProducts: async (params?: { search?: string; category?: number; product_type?: string; is_active?: boolean; low_stock?: 'true'; page?: number; page_size?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Product>>('/catalog/products/', { params })
    return data
  },

  getProduct: async (id: number): Promise<Product> => (await apiClient.get<Product>(`/catalog/products/${id}/`)).data,

  createProduct: async (payload: Partial<Product>): Promise<Product> => {
    const { data } = await apiClient.post<Product>('/catalog/products/', payload)
    return data
  },

  updateProduct: async (id: number, payload: Partial<Product>): Promise<Product> => {
    const { data } = await apiClient.put<Product>(`/catalog/products/${id}/`, payload)
    return data
  },

  deleteProduct: async (id: number): Promise<void> => {
    await apiClient.delete(`/catalog/products/${id}/`)
  },

  /** Productos activos con stock en o por debajo del mínimo */
  lowStock: async (params?: { page_size?: number }) =>
    (await apiClient.get<PaginatedResponse<Product>>('/catalog/low-stock/', { params })).data,

  // ── Categorías ─────────────────────────────────────────────────────────────
  listCategories: async (params?: { page?: number; page_size?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Category>>('/catalog/categories/', { params })
    return data
  },

  createCategory: async (payload: Partial<Category>): Promise<Category> => {
    const { data } = await apiClient.post<Category>('/catalog/categories/', payload)
    return data
  },

  updateCategory: async (id: number, payload: Partial<Category>): Promise<Category> => {
    const { data } = await apiClient.put<Category>(`/catalog/categories/${id}/`, payload)
    return data
  },

  deleteCategory: async (id: number): Promise<void> => {
    await apiClient.delete(`/catalog/categories/${id}/`)
  },
}
