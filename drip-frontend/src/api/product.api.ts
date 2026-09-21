import { client } from './client'
import type { Product, ProductListItem, Review } from '@/types/product'
import type { CursorPage, PaginatedResponse } from '@/types/api'

export interface ProductFilters {
  q?: string; category_id?: string; seller_id?: string
  min_price?: number; max_price?: number; on_sale?: boolean
  sort?: string; limit?: number; cursor?: string
}
export const productApi = {
  list:        (p: ProductFilters) => client.get<CursorPage<ProductListItem>>('/products', { params: p }).then(r => r.data),
  detail:      (id: string)        => client.get<Product>(`/products/${id}`).then(r => r.data),
  bySlug:      (slug: string)      => client.get<Product>(`/products/slug/${slug}`).then(r => r.data),
  suggestions: (q: string)         => client.get<{ suggestions: string[] }>('/products/search/suggestions', { params: { q } }).then(r => r.data),
  reviews:     (id: string, p?: object) => client.get<PaginatedResponse<Review>>(`/customers/reviews/product/${id}`, { params: p }).then(r => r.data),
  submitReview:(b: object)         => client.post<Review>('/customers/me/reviews', b).then(r => r.data),
}
