import apiClient from './client'
import type { Product, Category, PaginatedResponse } from '@/types'

export const inventoryApi = {
  // ── Productos ──────────────────────────────────────────────────────────────
  listProducts: async (params?: { search?: string; category?: number; product_type?: string; is_active?: boolean; page?: number; page_size?: number }) => {
    const { data } = await apiClient.get<PaginatedResponse<Product>>('/catalog/products/', { params })
    return data
  },

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
