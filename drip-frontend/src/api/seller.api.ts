import { client } from './client'
import type { SellerProfile, SellerDashboard, WalletBalance } from '@/types/seller'
import type { Product, ProductListItem } from '@/types/product'
import type { PaginatedResponse } from '@/types/api'

export const sellerApi = {
  register:       (b: object) => client.post('/seller/register', b).then(r => r.data),
  profile:        ()          => client.get<SellerProfile>('/seller/me').then(r => r.data),
  updateProfile:  (b: object) => client.patch<SellerProfile>('/seller/me', b).then(r => r.data),
  uploadLogo:     (f: File)   => {
    const fd = new FormData(); fd.append('logo', f)
    return client.post<{ logo_url: string }>('/seller/logo', fd).then(r => r.data)
  },
  dashboard:      (period = 'month') => client.get<SellerDashboard>('/seller/dashboard', { params: { period } }).then(r => r.data),
  products:       (p?: object) => client.get<PaginatedResponse<ProductListItem>>('/seller/products', { params: p }).then(r => r.data),
  createProduct:  (b: object)  => client.post<Product>('/seller/products', b).then(r => r.data),
  updateProduct:  (id: string, b: object) => client.put<Product>(`/seller/products/${id}`, b).then(r => r.data),
  deleteProduct:  (id: string) => client.delete(`/seller/products/${id}`).then(r => r.data),
  publishProduct: (id: string) => client.post(`/seller/products/${id}/publish`, {}).then(r => r.data),
  wallet:         ()           => client.get<WalletBalance>('/wallet/balance').then(r => r.data),
  orders:         (p?: object) => client.get('/seller/orders', { params: p }).then(r => r.data),
  inventory:      (p?: object) => client.get('/seller/inventory', { params: p }).then(r => r.data),
  adjustStock:    (variantId: string, b: object) =>
    client.post(`/seller/inventory/${variantId}/adjust`, b).then(r => r.data),
  bankAccounts:   ()           => client.get('/seller/bank-accounts').then(r => r.data),
  addBankAccount: (b: object)  => client.post('/seller/bank-accounts', b).then(r => r.data),
}
