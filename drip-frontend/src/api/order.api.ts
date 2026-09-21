import { client } from './client'
import type { Order, CartItem } from '@/types/order'
import type { PaginatedResponse } from '@/types/api'

export const cartApi = {
  get:    ()                     => client.get<{ items: CartItem[] }>('/cart').then(r => r.data),
  add:    (b: object)            => client.post('/cart', b).then(r => r.data),
  update: (id: string, b:object) => client.patch(`/cart/${id}`, b).then(r => r.data),
  remove: (id: string)           => client.delete(`/cart/${id}`).then(r => r.data),
  clear:  ()                     => client.post('/cart/clear', {}).then(r => r.data),
}
export const orderApi = {
  create:        (b: object)    => client.post<{ order_id: string; order_number: string }>(
                                     '/orders', b).then(r => r.data),
  list:          (p?: object)   => client.get<PaginatedResponse<Order>>('/orders', { params: p }).then(r => r.data),
  detail:        (id: string)   => client.get<Order>(`/orders/${id}`).then(r => r.data),
  cancel:        (id: string, b: object) => client.post(`/orders/${id}/cancel`, b).then(r => r.data),
  validateCoupon:(b: object)    => client.post<{ discount_amount: number; message: string }>(
                                     '/coupons/validate', b).then(r => r.data),
}
