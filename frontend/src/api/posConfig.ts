import apiClient from './client'

export interface RegisterConfig {
  id: number
  name: string
  location: number
  location_name: string
  is_active: boolean
  open_session_by: string | null
}

export type PaymentKind = 'cash' | 'card' | 'transfer' | 'wallet'

export interface PaymentMethodConfig {
  id: number
  code: string
  name: string
  kind: PaymentKind
  kind_label: string
  is_active: boolean
  sort: number
}

export interface Location { id: number; name: string; is_default: boolean; is_active: boolean }

export const PAYMENT_KINDS: [PaymentKind, string][] = [
  ['cash', 'Efectivo'], ['card', 'Tarjeta'], ['transfer', 'Transferencia'], ['wallet', 'Billetera digital'],
]

export const posConfigApi = {
  registers: async () => (await apiClient.get<RegisterConfig[]>('/cash/registers/config/')).data,
  createRegister: async (body: { name: string; location?: number }) =>
    (await apiClient.post<RegisterConfig>('/cash/registers/config/', body)).data,
  updateRegister: async (id: number, body: Partial<Pick<RegisterConfig, 'name' | 'location' | 'is_active'>>) =>
    (await apiClient.patch<RegisterConfig>(`/cash/registers/config/${id}/`, body)).data,
  methods: async () => (await apiClient.get<PaymentMethodConfig[]>('/sales/payment-methods/config/')).data,
  createMethod: async (body: { name: string; kind: PaymentKind }) =>
    (await apiClient.post<PaymentMethodConfig>('/sales/payment-methods/config/', body)).data,
  updateMethod: async (id: number, body: Partial<Pick<PaymentMethodConfig, 'name' | 'kind' | 'is_active'>>) =>
    (await apiClient.patch<PaymentMethodConfig>(`/sales/payment-methods/config/${id}/`, body)).data,
  locations: async () => (await apiClient.get<Location[]>('/tenant/locations/')).data,
}
